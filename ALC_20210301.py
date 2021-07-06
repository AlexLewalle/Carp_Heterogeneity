#!/usr/bin/env python

r"""    
Tidied up from   ALC_20210228.py.

"""

EXAMPLE_DESCRIPTIVE_NAME = "Electro-mechanical coupling"
EXAMPLE_AUTHOR = "Gernot Plank <gernot.plank@medunigraz.at>"

import os
import sys
from datetime import date
from math import log

from carputils import settings
from carputils import tools
from carputils import mesh
from carputils import model
from carputils import ep
from carputils.resources import petsc_options
from carputils import testing

def parser():
    parser = tools.standard_parser()
    group  = parser.add_argument_group('experiment specific options')

    group.add_argument('--ep-model',
                         default='monodomain',
                         choices=ep.MODEL_TYPES,
                         help='pick electrical model type')

    def zeroone(string):
        val = float(string)
        assert 0 <= val <= 1
        return val

    group.add_argument('--vd',
                        default=0.0, type=zeroone,
                        help='fudge factor on [0,1] to attenuate '
                             'force-velocity dependence')

    group.add_argument('--EP',  default='TT2',
                        choices=['TT2','TT2_Cai'],
                        help='pick human EP model')

    group.add_argument('--Stress', default='LandStress',
                        choices=['LandStress'],
                        help='pick stress model')

    group.add_argument('--length',
                        type=float, default=60.,
                        help='choose apicobasal length of wedge in mm')

    group.add_argument('--width',
                        type=float, default=20.,
                        help='choose circumferential width of wedge in mm')

    group.add_argument('--resolution',
                        type=float, default=2.0,
                        help='choose mesh resolution in mm')

    group.add_argument('--mechanics-off',
                        action='store_true',
                        help='switch off mechanics to generate activation vectors')

    group.add_argument('--duration',
                        type=float, default=100.,
                        help='duration of simulation (ms)')

    group.add_argument('--immersed',
                        action='store_true',
                        help='turn on immersed formulation with bath as container')

    return parser


def jobID(args):
    """
    Generate name of top level output directory.
    """
    today = date.today()
    return '{}_{}_{}_ab_{}_cw_{}'.format(today.isoformat(), args.EP, args.Stress, args.length, args.width)


@tools.carpexample(parser, jobID, clean_pattern='^(\d{4}-\d{2}-\d{2})|(mesh)|(exp)')
def run(args, job):
    import pdb; pdb.set_trace()
    # --- start building command line-----------------------------------------
    cmd  = tools.carp_cmd('em_coupling_AL.par')
    cmd +=[ '-simID', job.ID,
            '-tend', args.duration ]

    # --- Generate mesh ------------------------------------------------------
    meshname, geom, wedgeTags = build_wedge(args)
    cmd += [ '-meshname', meshname ]

    # --- set up mechanics materials------------------------------------------
    wedge = model.mechanics.GuccioneMaterial(wedgeTags, 'wedge',  kappa=1000., a=1.0 )

    # --- define stimuli -----------------------------------------------------
    stim = My_setupStimuli(geom)
    cmd += stim

    # --- define type of source model ---------------------------------------
    cmd += ep.model_type_opts(args.ep_model)

    # --- Define boundary conditions ----------------------------------------
    
    cmd += ['-num_mechanic_dbc', 1]

    # Dirichlet BC - fix 'apical face, no displacement in apico-basal direction'
    cmd += ['-mechanic_dbc[0].name', 'apex']
    cmd += mesh.block_boundary_condition(geom, 'mechanic_dbc', 0, 'y', lower=True)
    cmd += ['-mechanic_dbc[0].bctype',     0,
            '-mechanic_dbc[0].apply_ux',   1,
            '-mechanic_dbc[0].apply_uy',   1,
            '-mechanic_dbc[0].apply_uz',   1,
            '-mechanic_dbc[0].dump_nodes', 1]

    # # INHOMOGENEOUS Dirichlet BC - basal face, 
    # dbc += ['-mechanic_dbc[0].name', 'basal']
    # dbc += mesh.block_boundary_condition(geom, 'mechanic_dbc', 1, 'y',  lower=False, bath=args.immersed)
    # dbc += ['-mechanic_dbc[1].bctype',     1,  # <-- 1 for inhomogeneous
    #         '-mechanic_dbc[1].apply_ux',   1,
    #         '-mechanic_dbc[1].apply_uy',   1,
    #         '-mechanic_dbc[1].apply_uz',   1,
    #         '-mechanic_dbc[1].ux',         0,
    #         '-mechanic_dbc[1].uy',         5, # <-- magnitude of stretch
    #         '-mechanic_dbc[1].uy_file',    'traces/dbc_cube',
    #         '-mechanic_dbc[1].uz',         0,
    #         '-mechanic_dbc[1].apply_uz',   1,
    #         '-mechanic_dbc[1].apply_uz',   1,
            
    #         '-mechanic_dbc[1].dump_nodes', 1]       




    # --- solve mechanics ---------------------------------------------------
    cmd += [ '-mechDT', 1.0 * (not args.mechanics_off) ]

    # Add material options
    cmd += model.optionlist([wedge])

    # --- setup EP regions --------------------------------------------------
   
    ExternalModel = "/home/al12/Carp/MyModels/TT2_Cai.so" 
    imps = ['-num_external_imp' , 1]  
    imps += ['-external_imp', ExternalModel ]

    num_imp_regions = 1
    imps  += [ '-num_imp_regions', num_imp_regions ]

    imps += [ '-imp_region[0].im', args.EP] 
    if args.EP == 'TT2_Cai':
       imps += ['-imp_region[0].im_param', 'CaiClamp=0,CaiSET=70e-5']
    imps += [ '-imp_region[0].num_IDs',1] 
    imps += [ '-imp_region[0].ID[0]', 111 ]

    gregs  = [ '-num_gregions', 1]
    gregs += [ '-gregion[0].num_IDs', 1 ]
    gregs += [ '-gregion[0].ID[0]', 111 ]

    ekregs  = [ '-num_ekregions', 1 ]
    ekregs += [ '-ekregion[0].ID', 0 ]
    ekregs += [ '-ekregion[0].vel_f', 0.6,
             '-ekregion[0].vel_s', 0.4,
             '-ekregion[0].vel_n', 0.2 ]
    cmd += imps + gregs + ekregs


    # --- active stress setting ------------------------------------------------------------------------------------------------------
    

    cmd += [ '-imp_region[0].plugins', args.Stress ]

    # pick limit cycle state file
    if args.EP == 'TT2_Cai':
        #f = '/home/al12/Carp/MyModels/TT2_Cai_LandStress_1000ms.sv'
        f = '/home/al12/Carp/MyModels/TT2_Cai_LandStress_STATES.sv'
    else:
        f = './states/{}_{}_bcl_500_ms.sv'.format(args.EP,args.Stress)
    # check existence of state file
    if not os.path.isfile(f):
        print('State variable initialization file {} not found!'.format(f))
        sys.exit(-1)
    else:
        cmd += [ '-imp_region[0].im_sv_init', f ]
    
    
    dump_Cai = True
    cmd += [ '-num_gvecs', 1,
               '-gvec[0].name',  "Ca_i",
               '-gvec[0].ID[0]', "Ca_i",
               '-gvec[0].bogus', -10. ]

    # overrule default parameters of active stress model
    cmd  += [ '-imp_region[0].plug_param',              'T_ref=40,Ca_50ref=0.54,TRPN_50=0.5,n_TRPN=2.7,k_TRPN=0.14,n_xb=3.38,k_xb=4.9e-3']

    cmd += [ '-veldep', 0 ]






    # --- electromechanical coupling ----------------------------------------
    emCoupling = 'weak'
    cmd += setupEMCoupling(emCoupling)

    # --- configure solvers ----------------------------------------------
    pressure  = 0
    cmd += configureSolvers(args,pressure)

    if args.visualize:
        cmd += ['-gridout_i',    3,
                '-stress_value', 4]   ; print('COMMAND-LINE ARGUMENTS FED TO job.carp(cmd): '); print(cmd)

    # --- Run simulation -----------------------------------------------------
    job.carp(cmd)

    # --- Do meshalyzer visualization ----------------------------------------
    if args.visualize and not args.dry and not settings.platform.BATCH:

        # Prepare file paths
        geom = os.path.join(job.ID, os.path.basename(meshname)+'_i')

        if args.mechanics_off:

            # # view transmembrane voltage
            # view = 'wedge_vm.mshz'
            # data = os.path.join(job.ID, 'vm.igb.gz')
            # job.meshalyzer(geom, data, view)

            # # view fiber stretch
            # view = 'wedge_lambda.mshz'
            # data = os.path.join(job.ID, 'Lambda.igb.gz')
            # job.meshalyzer(geom, data, view)

            # if calcium-driven, show Cai transients
            if args.Stress != 'TanhStress':
                view = 'wedge_Cai.mshz'
                data = os.path.join(job.ID, 'Ca_i.igb.gz')
                job.meshalyzer(geom, data, view)

            # # view tension
            # view = 'wedge_tension.mshz'
            # data = os.path.join(job.ID, 'Tension.igb.gz')
            # job.meshalyzer(geom, data, view)

        else:

            # deformation data
            #if args.immersed:
            #    deform = os.path.join(job.ID, 'x_act.dynpt')
            #    job.gunzip(deform)
            #else:
            deform = os.path.join(job.ID, 'x.dynpt')
            job.gunzip(deform)

            # # view lambda first
            # view = 'wedge_lambda.mshz'
            # data = os.path.join(job.ID, 'Lambda.igb.gz')
            # job.meshalyzer(geom, data, deform, view)

            # if calcium-driven, show Cai transients
            if args.Stress != 'TanhStress':
                view = 'wedge_Cai.mshz'
                data = os.path.join(job.ID, 'Ca_i.igb.gz')
                job.meshalyzer(geom, data, deform, view)

            # view tension
            view = 'wedge_tension.mshz'
            data = os.path.join(job.ID, 'Tension.igb.gz')
            job.meshalyzer(geom, data, deform, view,     compsurf=True)



# ============================================================================
#    FUNCTIONS
# ============================================================================

def build_wedge(args):

    # Units are mm
    ab_len = args.length  # apico-basal length
    cc_len = args.width   # circumferential width
    w      = 10.0         # transmural wall thickness
    cu     =  0.0         # apicobasal length of cushion

    # if immersed, apply Dirichlet at basal pillow tissue
    if args.immersed:
        cu = 10.0

    geom = mesh.Block(size=(cc_len,ab_len+cu,w), resolution=args.resolution)


    geom.set_fibres(90,90, 90,90) #-60, 60, 90, 90)

    # apicobasal coordinates
    ab_0 = cu/2 - ab_len/2    
    ab_3 = cu/2 + ab_len/2

    # transmural coordinates
    tm_0 = -w/2
    tm_3 =  w/2

    # circumferential coordinates, no regions here
    cf_0 = -cc_len/2
    cf_1 =  cc_len/2


    active_wedge = mesh.BoxRegion((cf_0,ab_0,tm_0), (cf_1,ab_3,tm_3), tag=111)
    geom.add_region(active_wedge)
   
    wedgeTags = [111]

    # Generate and return base name
    meshname = mesh.generate(geom)

    return meshname, geom, wedgeTags





# --- set stimulus -----------------------------------------------------------
def My_setupStimuli(geom):

    lo, up = geom.tissue_limits()
    res    = geom.resolution()
    radius = 0.25

    #electrode = mesh.block_region(geom, 'stimulus', 0, [-radius, -radius, up[2]-res/2], [radius, radius, up[2]+res/2], False)
    #electrode = mesh.block_region(geom, 'stimulus', 0, [-lo[0],-lo[1]/2-res*3/2, -lo[2]], [+lo[0],+lo[1]/2+res*3/2, +lo[2]], False)
    electrode = mesh.block_region(geom, 'stimulus', 0, [lo[0]+res/2, 0 , lo[2]+res/2], [up[0]-res/2, 0, up[2]-res/2], False, True) # slice at y = 0
    #electrode = mesh.block_region(geom, 'stimulus', 0, [0, lo[1]+res/2, lo[2]+res/2], [0, up[1]-res/2, up[2]-res/2], False, True) # slice at x = 0
    #electrode = mesh.block_region(geom, 'stimulus', 0, [lo[0]+res/2, lo[1]+res/2 , 0], [up[0]-res/2, up[1]-res/2, 0 ], False, True) # slice at z = 0
    

    strength        = 150.0         # stimulus strength
    duration        =   3.0         # stimulus duration

    num_stim = 2

    stmOpts = [ '-floating_ground'     , '0',
                '-num_stim'            , num_stim,
                '-stimulus[0].stimtype', '0',
                '-stimulus[0].start'   , '5',
                '-stimulus[0].strength', str(strength),
                '-stimulus[0].duration', str(duration)]
    stmOpts += electrode

    ekstim = ['-stimulus[1].stimtype', 8 ]
    stmOpts += ekstim

    return stmOpts

# --- set up EP --------------------------------------------------------------



def setupDirichlet(geom,args):

    # figure out tissue limits
    lo, up = geom.tissue_limits()
    res    = geom.resolution()

    

    # dbc += ['-mechanic_dbc[0].name', 'epi']
    # dbc += mesh.block_boundary_condition(geom, 'mechanic_dbc', 0, 'z',
    #                                      lower=False, bath=args.immersed)

    # dbc += ['-mechanic_dbc[0].bctype',     0,
    #         '-mechanic_dbc[0].apply_ux',   1,
    #         '-mechanic_dbc[0].apply_uy',   1,
    #         '-mechanic_dbc[0].apply_uz',   1,
    #         '-mechanic_dbc[0].dump_nodes', 1]

    # fix a single node at the apical face
#   dbc += ['-mechanic_dbc[2].name', 'apex-center']
#
#   dbc += mesh.block_region(geom, 'mechanic_dbc', 2, [-res/2, lo[1]-res/2, -res/2],
#                                                     [+res/2, lo[1]+res/2, +res/2], False)
#   dbc += ['-mechanic_dbc[2].bctype',     0,
#           '-mechanic_dbc[2].apply_ux',   1,
#           '-mechanic_dbc[2].apply_uy',   0,
#           '-mechanic_dbc[2].apply_uz',   1,
#           '-mechanic_dbc[2].dump_nodes', 1]
#
#   dbc += ['-mechanic_dbc[2].name', 'anterior']
#   dbc += mesh.block_boundary_condition(geom, 'mechanic_dbc', 2, 'x',
#                                        lower=True, bath=args.immersed)
#   dbc += ['-mechanic_dbc[2].bctype',     0,
#           '-mechanic_dbc[2].apply_ux',   1,
#           '-mechanic_dbc[2].apply_uy',   0,
#           '-mechanic_dbc[2].apply_uz',   0,
#           '-mechanic_dbc[2].dump_nodes', 1]
#
#    dbc += ['-mechanic_dbc[3].name', 'posterior']
#    dbc += mesh.block_boundary_condition(geom, 'mechanic_dbc', 3, 'x',
#                                         lower=False, bath=args.immersed)
#    dbc += ['-mechanic_dbc[3].bctype',     0,
#            '-mechanic_dbc[3].apply_ux',   1,
#            '-mechanic_dbc[3].apply_uy',   0,
#            '-mechanic_dbc[3].apply_uz',   0,
#            '-mechanic_dbc[3].dump_nodes', 1]
    return dbc






# --- setup electromechanical coupling ---------------------------------------
def setupEMCoupling (emCoupling):

    if(emCoupling == 'weak'):
        coupling = ['-mech_use_actStress', 1, '-mech_lambda_upd', 1, '-mech_deform_elec', 0]
    elif(emCoupling == 'strong'):
        coupling = ['-mech_use_actStress', 1, '-mech_lambda_upd', 2, '-mech_deform_elec', 1]
    elif(emCoupling == 'none'):
        coupling = ['-mech_use_actStress', 0, '-mech_lambda_upd', 0, '-mech_deform_elec', 0]

    return coupling


# --- configure solver options -----------------------------------------------
def configureSolvers(args, pressure):

    # --- Configuration variables --------------------------------------------
    configuration   =  1            # 0 Euler, 1 Lagrangian
    line_search     =  0            # use line-search method in Newton
    active_imp      =  0            # identify active region
    tangent_mode    =  1            # (0) symbolic tangent, (1) numerical tangent

    # Add options
    mech_opts = [ '-dt',                   25.,
                  '-mech_configuration',   configuration,
                  '-mech_tangent_comp',    tangent_mode,
                  '-volumeTracking',       1 ,
                  '-newton_line_search',   line_search,
                  '-newton_maxit_mech',    50,
                  '-load_stiffening',      1 * (pressure>0),
                  '-mapping_mode',         1,
                  '-newton_tol_mech',      1e-6,
                  '-mech_output',          1 ]

    # Specify solver settings
    ep_opts = [ '-parab_solve',        1,
                '-localize_pts',       1,
                '-cg_tol_ellip',       1e-8,
                '-cg_tol_parab',       1e-8,
                '-cg_norm_ellip',      0,
                '-cg_norm_parab',      0,
                '-mapping_mode',       1,
                '-mass_lumping',       1]

    return ep_opts + mech_opts


if __name__ == '__main__':
    run()
