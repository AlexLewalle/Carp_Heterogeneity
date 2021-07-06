#!/usr/bin/env python

r"""    ALTERED FROM   ALC_20210228.py



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

    group.add_argument('--EP',  default='TT2_Cai',
                        choices=['TT2','GPB', 'TT2_Cai'],
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

    group.add_argument('--pCa',
                        type=float, default=-7.,
                        help='Set pCa')

    group.add_argument('--maxpressure',
                        type=float, default=1,
                        help='Maximum pressure applied to the basal surface.')

    group.add_argument('--initfile',
                        type=str, default='states/temp_state.sv',
                        help='State file input.')

    group.add_argument('--ifinit',
                        choices=['r', 'init', 'no_init'],
                        default='no_init',
                        help='State file output.')

    return parser


def jobID(args):
    """
    Generate name of top level output directory.
    """
    today = date.today()
    return '{}_{}_{}_ab_{}_cw_{}'.format(today.isoformat(), args.EP, args.Stress, args.length, args.width)


@tools.carpexample(parser, jobID, clean_pattern='^(\d{4}-\d{2}-\d{2})|(mesh)|(exp)')
def run(args, job):
    #import pdb; pdb.set_trace()
    # --- start building command line-----------------------------------------
    cmd  = tools.carp_cmd('em_coupling_AL.par')
    cmd +=[ '-simID', job.ID,
            '-tend', args.duration ]

    # Choose whether to save or load initialisation for simulation
    if args.ifinit=='init':
        #cmd += ['-write_statef', '/home/al12/Carp/Heterogeneity/states/'+args.initfile] # Doesn't seem to do anything
        cmd += ['-chkpt_start', args.duration]
        cmd += ['-chkpt_stop', args.duration]
        cmd += ['-chkpt_intv', 1]
    elif args.ifinit=='r':
            cmd += ['-start_statef', args.ID+'_init/checkpoint.100.0']



    # --- Generate mesh ------------------------------------------------------
    meshname, geom, wedgeTags, cushTags = build_wedge(args)
    cmd += [ '-meshname', meshname ]

    # --- set up mechanics materials------------------------------------------
    wedge, cushion = setupMechMat(args,wedgeTags,cushTags)

    # --- define stimuli -----------------------------------------------------
    stim = My_setupStimuli(geom)
    cmd += stim

    # --- define type of source model ---------------------------------------
    cmd += ep.model_type_opts(args.ep_model)

    # --- Define boundary conditions ----------------------------------------

    # Variable Neumann BC - basal face, 
    pressure_scaling = - args.maxpressure
    cmd += ['-num_mechanic_nbc', 1]
    cmd += mesh.block_boundary_condition(geom, 'mechanic_nbc', 0, 'y',  lower=False, bath=args.immersed)
    cmd += ['-mechanic_nbc[0].name', 'basal_nbc',
            '-mechanic_nbc[0].pressure', pressure_scaling,
            '-mechanic_nbc[0].trace', 'traces/dbc_cube_AL',
            '-mechanic_nbc[0].dump_surf', 1] 

    # HOMOGENEOUS Dirichlet BC - face, 
    cmd += ['-num_mechanic_dbc', 1]
    cmd += mesh.block_boundary_condition(geom, 'mechanic_dbc', 0, 'y',  lower=True, bath=args.immersed)
    cmd += ['-mechanic_dbc[0].name', 'apical_dbc']
    cmd += ['-mechanic_dbc[0].bctype',     0,  # <-- 1 for inhomogeneous, 0 for homogeneous
            '-mechanic_dbc[0].apply_ux',   1,
            '-mechanic_dbc[0].apply_uy',   1,
            '-mechanic_dbc[0].apply_uz',   1,
            '-mechanic_dbc[0].dump_nodes', 1]       

    #    # HOMOGENEOUS Dirichlet BC - face, 
    # cmd += mesh.block_boundary_condition(geom, 'mechanic_dbc', 1, 'y',  lower=False, bath=args.immersed)
    # cmd += ['-mechanic_dbc[0].name', 'basal_lateral']
    # cmd += ['-mechanic_dbc[0].bctype',     0,  # <-- 1 for inhomogeneous, 0 for homogeneous
    #         '-mechanic_dbc[0].apply_ux',   0,
    #         '-mechanic_dbc[0].apply_uy',   0,
    #         '-mechanic_dbc[0].apply_uz',   0,
    #         '-mechanic_dbc[0].dump_nodes', 1]       





    # --- solve mechanics ---------------------------------------------------
    mydt = 1
    cmd += [ '-mechDT', mydt* (not args.mechanics_off) ,
                '-spacedt', mydt,
                '-timedt', mydt,
                '-dt', mydt]


    # Add material options
    if args.immersed:
        cmd += model.optionlist([wedge,cushion])
    else:
        cmd += model.optionlist([wedge])

    # --- setup EP regions --------------------------------------------------
    imps, gregs, ekregs = setupEP(wedgeTags,cushTags, args)
    cmd += imps + gregs + ekregs


    # --- active stress setting ---------------------------------------------
    active_imp = 0  # define active imp region
    cmd += setupActive (args.Stress, args.EP, active_imp, args.vd)

    # --- electromechanical coupling ----------------------------------------
    emCoupling = 'weak'
    cmd += setupEMCoupling(emCoupling)

    # --- configure solvers -------------------------------------------------
    pressure = 0 
    cmd += configureSolvers(args,pressure)

    #if args.visualize:
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
            # data = os.path.oin(job.ID, 'vm.igb.gz')
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

            # # view tension
            # view = 'wedge_tension.mshz'
            # data = os.path.join(job.ID, 'Tension.igb.gz')
            # job.meshalyzer(geom, data, deform, view,     compsurf=True)



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

    # if immersed, apply Dirichlet at basal pillow tissue
    #if args.immersed:
    #    geom.set_bath(thickness=(0,bw,0), both_sides=True)

    # Set fibre angle to 0, sheet angle to 90
    geom.set_fibres(90,90, 90,90) #-60, 60, 90, 90)

    # Define regions
    # apicobasal coordinates
    ab_0 = cu/2 - ab_len/2
    ab_1 = cu/2 - ab_len/2 + 0.33*ab_len
    ab_2 = cu/2 - ab_len/2 + 0.66*ab_len
    ab_3 = cu/2 + ab_len/2

    # transmural coordinates
    tm_0 = -w/2
    tm_1 = -w/2 + 0.33*w
    tm_2 = -w/2 + 0.66*w
    tm_3 =  w/2

    # circumferential coordinates, no regions here
    cf_0 = -cc_len/2
    cf_1 =  cc_len/2

    # define epicardial layer
    epi_apex = mesh.BoxRegion((cf_0,ab_0,tm_0), (cf_1,ab_1,tm_1), tag=11)
    geom.add_region(epi_apex)
    epi_mid  = mesh.BoxRegion((cf_0,ab_1,tm_0), (cf_1,ab_2,tm_1), tag=12)
    geom.add_region(epi_mid)
    epi_base = mesh.BoxRegion((cf_0,ab_2,tm_0), (cf_1,ab_3,tm_1), tag=13)
    geom.add_region(epi_base)

    # define midmyocardial layer
    mid_apex = mesh.BoxRegion((cf_0,ab_0,tm_1), (cf_1,ab_1,tm_2), tag=21)
    geom.add_region(mid_apex)
    mid_mid  = mesh.BoxRegion((cf_0,ab_1,tm_1), (cf_1,ab_2,tm_2), tag=22)
    geom.add_region(mid_mid)
    mid_base = mesh.BoxRegion((cf_0,ab_2,tm_1), (cf_1,ab_3,tm_2), tag=23)
    geom.add_region(mid_base)

    # define endocardial layer
    endo_apex = mesh.BoxRegion((cf_0,ab_0,tm_2), (cf_1,ab_1,tm_3), tag=31)
    geom.add_region(endo_apex)
    endo_mid  = mesh.BoxRegion((cf_0,ab_1,tm_2), (cf_1,ab_2,tm_3), tag=32)
    geom.add_region(endo_mid)
    endo_base = mesh.BoxRegion((cf_0,ab_2,tm_2), (cf_1,ab_3,tm_3), tag=33)
    geom.add_region(endo_base)

    wedgeTags = [11, 12, 13, 21, 22, 23, 31, 32, 33]

    # define cushion
    cushTags = []
    if args.immersed:
       cushTags += [0]
       cushion = mesh.BoxRegion((cf_0,ab_0-cu,tm_0), (cf_1,ab_0,tm_3), tag=0)
       geom.add_region(cushion)


    # Generate and return base name
    meshname = mesh.generate(geom)

    return meshname, geom, wedgeTags, cushTags


# --- set up mechanic materials ----------------------------------------------
def setupMechMat(args,wedgeTags,cushTags):

    wedge   = []
    cushion = []
    # --- Material definitions ------------------------------------------------
    #wedge = model.mechanics.LinearMaterial([0], 'tissue', nu=0.4, E=100.)
    #wedge = model.mechanics.StVenantKirchhoffMaterial([0], 'tissue', mu=37.3, lam=40)
    #wedge = model.mechanics.MooneyRivlinMaterial([0], 'tissue', c_1=30, c_2=20)
    #wedge = model.mechanics.DemirayMaterial([0], 'tissue', a=0.345)
    #wedge = model.mechanics.HolzapfelArterialMaterial([0], 'tissue', c=5.0)
    #wedge = model.mechanics.HolzapfelOgdenMaterial([0], 'tissue', a=3.3345)
    wedge = model.mechanics.GuccioneMaterial(wedgeTags, 'wedge',  kappa=1000., a=1.0 )
    #wedge = model.mechanics.AnisotropicMaterial([0], 'tissue', kappa=100, c=30)
    #wedge = model.mechanics.NeoHookeanMaterial([0], 'tissue', kappa=100, c=25)

    # 0 for symbolic tangent computation, 1 for numeric approximation
    #tangent_mode = 1
    #if (args.resolution < 0.02): # for finer meshes we take another material
    #    wedge = model.mechanics.GuccioneMaterial(wedgeTags, 'wedge', kappa=500.,a=0.876)
    #    tangent_mode = 1             # use approximate tangent computation
    if args.immersed:
       #cushion = model.mechanics.DemirayMaterial(cushTags, 'cushion', kappa=1000, a=33.)
       cushion = model.mechanics.NeoHookeanMaterial(cushTags, 'cushion', kappa=100, c=10)

    return wedge, cushion


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
def setupEP(wedge,cushion, args):

   imps = []
   
   ExternalModel = "/home/al12/Carp/MyModels/TT2_Cai.so" 
   import os.path
   print('External model path exists = ' + str(os.path.exists(ExternalModel)) + '  <<<<<<<<<<<<<<<<<<<<<<<<<<<<')
   imps += ['-num_external_imp' , 1]  
   imps += ['-external_imp', ExternalModel ]
   

   num_imp_regions = 2
   imps  += [ '-num_imp_regions', num_imp_regions ]

   imps += [ '-imp_region[0].im', args.EP] #'converted_TT2_Cai']                 # <--- AL 17/02/2021
   if args.EP == 'TT2_Cai':
       imps += ['-imp_region[0].im_param', 'CaiClamp=0,CaiSET='+str(10**(args.pCa+3)) ]
   imps += [ '-imp_region[0].num_IDs', len(wedge)] #+len(cushion) ]
   for ind, reg in enumerate(wedge): # + cushion):
       imps += [ '-imp_region[0].ID[%d]'%(ind), reg ]



   imps += [ '-imp_region[1].im', args.EP ] #'converted_TT2_Cai' ]                # <--- AL 17/02/2021
   imps += [ '-imp_region[1].num_IDs', len(cushion) ]
   #imps += ['-imp_region[1].im', 'TT2']
   imps += [ '-imp_region[1].im_param', 'GNa*0.' ]
   for ind, reg in enumerate(cushion):
       imps += [ '-imp_region[1].ID[%d]'%(ind), reg ]

   gregs  = [ '-num_gregions', 2 ]
   gregs += [ '-gregion[0].num_IDs', len(wedge) ]
   for ind, reg in enumerate(wedge):
       gregs += [ '-gregion[0].ID[%d]'%(ind), reg ]

   gregs += [ '-gregion[1].num_IDs', len(cushion) ]
   for ind, reg in enumerate(cushion):
       gregs += [ '-gregion[1].ID[%d]'%(ind), reg ]

   gregs += [ '-gregion[1].g_il', 0.001,
              '-gregion[1].g_el', 0.001,
              '-gregion[1].g_it', 0.001,
              '-gregion[1].g_et', 0.001,
              '-gregion[1].g_in', 0.001,
              '-gregion[1].g_en', 0.001  ]

   eks  = [ '-num_ekregions', 2 ]
   eks += [ '-ekregion[0].ID', 0 ]
   eks += [ '-ekregion[0].vel_f', 0.6,
            '-ekregion[0].vel_s', 0.4,
            '-ekregion[0].vel_n', 0.2 ]

   eks += [ '-ekregion[1].ID', 1 ]
   eks += [ '-ekregion[1].ignore', 1 ]

   return imps, gregs, eks





# --- setup active stress setting --------------------------------------------
def setupActive (Stress, EP, active_imp, veldep):

    opts      = []
    im_pars   = []
    statefile = False


        # pick EP and Stress model
        #im_pars += [ '-imp_region[{0}].im'.format(active_imp), EP ]           REDUNDANT FROM L.561!
    im_pars += [ '-imp_region[{0}].plugins'.format(active_imp), Stress ]

        # pick limit cycle state file
    if EP == 'TT2_Cai':
        f = '/home/al12/Carp/MyModels/TT2_Cai_LandStress_STATES.sv'
    else:
        f = './states/{}_{}_bcl_500_ms.sv'.format(EP,Stress)
    statefile = True

    dump_Cai = True
    dmpCai = [ '-num_gvecs', 1,
                   '-gvec[0].name',  "Ca_i",
                   '-gvec[0].ID[0]', "Ca_i",
                   '-gvec[0].bogus', -10. ]

    im_pars += dmpCai


    # overrule default parameters of active stress model

    activeStressPars = setupStressParams(EP,Stress,active_imp)
    im_pars  += activeStressPars


    opts += [ '-veldep', veldep ]
    opts += im_pars

    # check existence of state file
    if statefile:
        if not os.path.isfile(f):
            print('State variable initialization file {} not found!'.format(f))
            sys.exit(-1)
        else:
            opts += [ '-imp_region[{0}].im_sv_init'.format(active_imp), f ]

    return opts


# --- set active stress parameters -------------------------------------------
def setupStressParams(EP, Stress, active_imp):

    params = []

    if EP != 'GPB':

         if Stress == 'LandStress' or Stress == 'LandStress_Cai' or Stress == 'LandStress_Cai_lambda':
             # LandStress parameter string
             p = 'T_ref=40,Ca_50ref=0.54,TRPN_50=0.5,n_TRPN=2.7,k_TRPN=0.14,n_xb=3.38,k_xb=4.9e-3'
         else:
             # TanhStress
             p = 't_emd=15,Tpeak=40,tau_c0=60,tau_r=110,t_dur=400,lambda_0=0.7,ld=5,ld_up=500,VmThresh=-60,ldOn=1'

         params  += [ '-imp_region[{0}].plug_param'.format(active_imp), p ]

    else:
        # GPB_Land stress parameters
        p  = 'T_ref=117.1,Ca_50ref=0.52,TRPN_50=0.37,n_TRPN=1.54'
        p += ',k_TRPN=0.14,n_xb=3.38,k_xb=4.9e-3,lengthDep=1'

        params  += [ '-imp_region[{0}].im_param'.format(active_imp), p ]

    return params


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
    mech_opts = [ #'-dt',                   25.,
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
