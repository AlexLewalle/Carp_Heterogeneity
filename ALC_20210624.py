#!/usr/bin/env python

r"""    ALTERED FROM   ALC_20210609.py

Isometric block contraction with necrotic fraction.

Change from 20210609: specify the Tref for the necrotic region.

"""

EXAMPLE_DESCRIPTIVE_NAME = "Electro-mechanical coupling"
EXAMPLE_AUTHOR = "Gernot Plank <gernot.plank@medunigraz.at>"

import os
import sys
from datetime import date
from math import log
import numpy as np

from carputils import settings
from carputils import tools
from carputils import mesh
from carputils import model
from carputils import ep
from carputils.resources import petsc_options
from carputils import testing

import ALCarpLib as alcl

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

    group.add_argument('--Stress', default='LandHumanStress',
                        choices=['LandHumanStress'],
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
                        type=float, default=7.0,
                        help='Set pCa')

    group.add_argument('--Tref',
                        type=float, default=40.0,
                        help='Set Tref for the healthy (non-necrotic) tissue')

    group.add_argument('--Trefnec',
                        type=float, default=0.0,
                        help='Set Tref for the necrotic tissue')

    group.add_argument('--fracnecrotic',
                        type=float, default=0.0,
                        help='Fraction of necrotic cells in the tissue.')

    group.add_argument('--savechkpt',
                        type=int,
                        choices=[1,0],
                        default=0,
                        help='Decide whether or not to save chkpt file at end of run.')
    group.add_argument('--loadchkpttime',
                        default='not_specified',
                        help='Specify time of checkpoint to load.')

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
    SavedState = '/home/al12/Carp/Heterogeneity/20210520/a/savedstate'
    if args.savechkpt == 1:
        cmd += ['-write_statef', SavedState]
        cmd += ['-num_tsav', 1, 
                '-tsav[0]',  args.duration ]
        # cmd += ['-chkpt_start', args.duration]
        # cmd += ['-chkpt_stop', args.duration]
        # cmd += ['-chkpt_intv', 1]
    if args.loadchkpttime != 'not_specified':
        cmd += ['-start_statef', SavedState+'.'+args.loadchkpttime+'.0']
    # elif args.ifinit=='r':
    #         cmd += ['-start_statef', args.ID+'_init/checkpoint.100.0']



    # --- Generate mesh ------------------------------------------------------
    meshname, geom, wedgeTags, cushTags = build_wedge(args)
    cmd += [ '-meshname', meshname ]

        # Retag selected elements as 666
    NumElem = 7500  # number of elements in block_i.elem
    FracNecrotic = args.fracnecrotic #0.01
    necrosisTags = [666]
    MyMask = np.array([True for i in range(0, int(NumElem*FracNecrotic)) ] + [False for i in range(int(NumElem*FracNecrotic), NumElem) ] )
    np.random.seed(0) # AL added 23/06/21
    np.random.shuffle(MyMask)  

    File1 = open(f"NecroticElements_{FracNecrotic}.regele", 'w')
    File1.write(str(int(NumElem*FracNecrotic)) + '\n')
    for i, x in enumerate(MyMask):
        if x:
            File1.write(str(i) + '\n')
    File1.close()
    dyn_reg = ['-numtagreg', 1]
    dyn_reg += ['-tagreg[0].type', 4]  # 4: define elements in elemfile.
    dyn_reg += ['-tagreg[0].elemfile', f"NecroticElements_{FracNecrotic}"]
    dyn_reg += ['-tagreg[0].tag', necrosisTags[0]]
    cmd += dyn_reg


    # --- set up mechanics materials------------------------------------------
    wedge, necrosis = setupMechMat(args,wedgeTags,necrosisTags)

    # --- define stimuli -----------------------------------------------------
    stim = My_setupStimuli(geom)
    cmd += stim

    # --- define type of source model ---------------------------------------
    cmd += ep.model_type_opts(args.ep_model)

    # --- Define boundary conditions ----------------------------------------

    # HOMOGENEOUS Dirichlet BC - apical face, 
    cmd += ['-num_mechanic_dbc', 2]
    cmd += mesh.block_boundary_condition(geom, 'mechanic_dbc', 0, 'y',  lower=True, bath=args.immersed)
    cmd += ['-mechanic_dbc[0].name', 'apical_dbc.surf']
    cmd += ['-mechanic_dbc[0].bctype',     0,  # <-- 1 for inhomogeneous, 0 for homogeneous
            '-mechanic_dbc[0].apply_ux',   1,
            '-mechanic_dbc[0].apply_uy',   1,
            '-mechanic_dbc[0].apply_uz',   1,
            '-mechanic_dbc[0].dump_nodes', 1]       

    # HOMOGENEOUS Dirichlet BC - basal face, 
    cmd += mesh.block_boundary_condition(geom, 'mechanic_dbc', 1, 'y',  lower=False, bath=args.immersed)
    cmd += ['-mechanic_dbc[1].name', 'basal_dbc.surf']
    cmd += ['-mechanic_dbc[1].bctype',     0,  # <-- 1 for inhomogeneous, 0 for homogeneous
            '-mechanic_dbc[1].apply_ux',   0,
            '-mechanic_dbc[1].apply_uy',   1,
            '-mechanic_dbc[1].apply_uz',   0,
            '-mechanic_dbc[1].dump_nodes', 1]  




    # --- solve mechanics ---------------------------------------------------
    mydt = 1
    cmd += [ '-mechDT', mydt* (not args.mechanics_off) ,
                '-spacedt', mydt * 10,          # time interval for saved data
                '-timedt', mydt,
                '-dt', mydt]


    # Add material options
    if args.immersed:
        cmd += model.optionlist([wedge,cushion])
    else:
        cmd += model.optionlist([wedge,necrosis])

    # --- setup EP regions --------------------------------------------------
    imps, gregs, ekregs = setupEP(wedgeTags,necrosisTags, args)
    cmd += imps + gregs + ekregs


    # --- active stress setting ---------------------------------------------
    active_imp = [0,1]  # define active imp region
    # cmd += setupActive (args.Stress, args.EP, active_imp, args.vd)
    cmd += setupActive ('LandHumanStress', args.EP, active_imp, args.vd, args.Tref, args.Trefnec)

    # --- electromechanical coupling ----------------------------------------
    emCoupling = 'weak'
    cmd += setupEMCoupling(emCoupling)

    # --- configure solvers -------------------------------------------------
    pressure = 0 
    cmd += configureSolvers(args,pressure)

    #if args.visualize:
    cmd += ['-gridout_i',    3,
            '-stress_value', 48]   # 16 needed to output 3x3 tensor ()
    print('COMMAND-LINE ARGUMENTS FED TO job.carp(cmd): '); print(cmd)


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

            # # if calcium-driven, show Cai transients
            # if args.Stress != 'TanhStress':
            #     view = 'wedge_Cai.mshz'
            #     data = os.path.join(job.ID, 'Ca_i.igb.gz')
            #     job.meshalyzer(geom, data, deform, view)

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


    geom = mesh.Block(size=(cc_len,ab_len+cu,w), resolution=args.resolution)

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

    healthytissue = mesh.BoxRegion((cf_0,ab_0,tm_0), (cf_1,ab_3,tm_3), tag=1)
    wedgeTags = [1]

    

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
def setupMechMat(args,wedgeTags,necrosisTags):

    wedge   = []
    cushion = []
    necrosis = []
    # --- Material definitions ------------------------------------------------
    #wedge = model.mechanics.LinearMaterial([0], 'tissue', nu=0.4, E=100.)
    #wedge = model.mechanics.StVenantKirchhoffMaterial([0], 'tissue', mu=37.3, lam=40)
    #wedge = model.mechanics.MooneyRivlinMaterial([0], 'tissue', c_1=30, c_2=20)
    #wedge = model.mechanics.DemirayMaterial([0], 'tissue', a=0.345)
    #wedge = model.mechanics.HolzapfelArterialMaterial([0], 'tissue', c=5.0)
    #wedge = model.mechanics.HolzapfelOgdenMaterial([0], 'tissue', a=3.3345)
    wedge = model.mechanics.GuccioneMaterial(wedgeTags, 'wedge',  kappa=1000., a=1.0 )
    necrosis = model.mechanics.GuccioneMaterial(necrosisTags, 'necrosis',  kappa=1000., a=1.0 )   # ##### Should this read necrosisTag ???

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

    return wedge, necrosis #cushion


# --- set stimulus -----------------------------------------------------------
def My_setupStimuli(geom):

    lo, up = geom.tissue_limits()
    res    = geom.resolution()
    radius = 0.25

    #electrode = mesh.block_region(geom, 'stimulus', 0, [-radius, -radius, up[2]-res/2], [radius, radius, up[2]+res/2], False)
    #electrode = mesh.block_region(geom, 'stimulus', 0, [-lo[0],-lo[1]/2-res*3/2, -lo[2]], [+lo[0],+lo[1]/2+res*3/2, +lo[2]], False)
    # electrode = mesh.block_region(geom, 'stimulus', 0, [lo[0]+res/2, 0 , lo[2]+res/2], [up[0]-res/2, 0, up[2]-res/2], False, True) # slice at y = 0
    electrode = mesh.block_region(geom, 'stimulus', 0, [lo[0], lo[1] , lo[2]], [up[0], up[1], up[2]], False, True) # slice at y = 0
    #electrode = mesh.block_region(geom, 'stimulus', 0, [0, lo[1]+res/2, lo[2]+res/2], [0, up[1]-res/2, up[2]-res/2], False, True) # slice at x = 0
    #electrode = mesh.block_region(geom, 'stimulus', 0, [lo[0]+res/2, lo[1]+res/2 , 0], [up[0]-res/2, up[1]-res/2, 0 ], False, True) # slice at z = 0
    

    strength        = 150.0         # stimulus strength
    duration        =   3.0         # stimulus duration

    num_stim = 2

    stmOpts = [ '-floating_ground'     , '0',
                '-diffusionOn'         , '0',
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
def setupEP(wedge,necrosis, args):

    imps = []
   
    ExternalModel = "/home/al12/Carp/MyModels/TT2_Cai.so" 
    import os.path
    print('External model path exists = ' + str(os.path.exists(ExternalModel)) + '  <<<<<<<<<<<<<<<<<<<<<<<<<<<<')
    imps += ['-num_external_imp' , 1]  
    imps += ['-external_imp', ExternalModel ]
   

    num_imp_regions = 2
    imps  += [ '-num_imp_regions', num_imp_regions ]

    imps += [ '-imp_region[0].im', args.EP] 
    if args.EP == 'TT2_Cai':
       imps += ['-imp_region[0].im_param', 'CaiClamp=0,CaiSET='+str(10**(-args.pCa+3))]  #str(args.CaiSET)]
    imps += [ '-imp_region[0].num_IDs', len(wedge)] 
    for ind, reg in enumerate(wedge): 
       imps += [ '-imp_region[0].ID[%d]'%(ind), reg ]

    imps += [ '-imp_region[1].im', args.EP] 
    if args.EP == 'TT2_Cai':
       imps += ['-imp_region[1].im_param', 'CaiClamp=0,CaiSET='+str(10**(-args.pCa+3)) ]
    imps += [ '-imp_region[1].num_IDs', len(necrosis)] 
    for ind, reg in enumerate(necrosis): 
       imps += [ '-imp_region[1].ID[%d]'%(ind), reg ]


    gregs  = [ '-num_gregions', 2 ]
    gregs += [ '-gregion[0].num_IDs', len(wedge) ]
    for ind, reg in enumerate(wedge):
        gregs += [ '-gregion[0].ID[%d]'%(ind), reg ]

    gregs += [ '-gregion[1].num_IDs', len(necrosis) ]
    for ind, reg in enumerate(necrosis):
        gregs += [ '-gregion[1].ID[%d]'%(ind), reg ]

    eks  = [ '-num_ekregions', 2 ]
    eks += [ '-ekregion[0].ID', 0 ]
    eks += [ '-ekregion[0].vel_f', 0.6,
            '-ekregion[0].vel_s', 0.24,
            '-ekregion[0].vel_n', 0.24 ]
    eks += [ '-ekregion[1].ID', 0 ]
    eks += [ '-ekregion[1].vel_f', 0.6,
            '-ekregion[1].vel_s', 0.4,
            '-ekregion[1].vel_n', 0.2 ]            

    return imps, gregs, eks





# --- setup active stress setting --------------------------------------------
def setupActive (Stress, EP, active_imp, veldep, Tref, Trefnec=0):

    opts      = []
    im_pars   = []
    statefile = False


        # pick EP and Stress model
        #im_pars += [ '-imp_region[{0}].im'.format(active_imp), EP ]           REDUNDANT FROM L.561!
    im_pars += [ '-imp_region[{0}].plugins'.format(active_imp[0]), Stress ]
    im_pars += [ '-imp_region[{0}].plugins'.format(active_imp[1]), Stress ]

        # pick limit cycle state file
    # if EP == 'TT2_Cai' and Stress=='LandStress' :
    #     f = '/home/al12/Carp/MyModels/TT2_Cai_LandStress_STATES.sv'
    # else:
    #     f = './states/{}_{}_bcl_500_ms.sv'.format(EP,Stress)
    # statefile = True

    # overrule default parameters of active stress model

    dump_Cai = True
    dmpCai = [ '-num_gvecs', 1,
                   '-gvec[0].name',  "Ca_i",
                   '-gvec[0].ID[0]', "Ca_i",
                   '-gvec[0].bogus', -10. ]
    im_pars += dmpCai

    activeStressPars = setupStressParams(EP,Stress,active_imp, Tref, Trefnec)
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
def setupStressParams(EP, Stress, active_imp, Tref, Trefnec=0):

    params = []
    p=[]
    
    # LandStress parameter string
    # p = 'T_ref=40,Ca_50ref=0.54,TRPN_50=0.5,n_TRPN=2.7,k_TRPN=0.14,n_xb=3.38,k_xb=4.9e-3'
    p += [f'Tref={Tref}']     #for active_imp[0]     HEALTHY TISSUE
    p += [f'Tref={Trefnec}']      #for active_imp[1]     NECROTIC TISSUE
    
    params  += [ '-imp_region[{0}].plug_param'.format(active_imp[0]), p[0] ]
    params  += [ '-imp_region[{0}].plug_param'.format(active_imp[1]), p[1] ]

    return params


# --- setup electromechanical coupling ---------------------------------------
def setupEMCoupling (emCoupling):

    if(emCoupling == 'weak'):
        coupling = ['-mech_use_actStress', 1, '-mech_lambda_upd', 2, '-mech_deform_elec', 0]
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
    tangent_mode    =  0            # (0) symbolic tangent, (1) numerical tangent

    # Add options
    mech_opts = [ #'-dt',                   25.,
                  '-mech_configuration',   configuration,
                  '-mech_tangent_comp',    tangent_mode,
                  '-volumeTracking',       1 ,
                  '-newton_line_search',   line_search,
                  '-newton_maxit_mech',    50,
                  '-load_stiffening',      1,
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
