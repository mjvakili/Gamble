import os 
import sys
import numpy as np
import emcee
from numpy.linalg import solve
from emcee.utils import MPIPool
import scipy.optimize as op
from numpy.linalg import solve

# --- Local ---
import util
import data as Data
from dechod import MCMC_model
from prior import PriorRange


def lnPost(theta, **kwargs):
    def lnprior(theta, **kwargs):
        '''log prior 
        '''
        fake_obs = kwargs['data']
    	fake_obs_icov = kwargs['data_icov']
    	kwargs.pop('data', None)
    	kwargs.pop('data_icov', None)
    	prior_range = kwargs['prior_range']
    	prior_min = prior_range[:,0]
    	prior_max = prior_range[:,1]
    	# Prior 
        if prior_min[0] < theta[0] < prior_max[0] and \
       	    prior_min[1] < theta[1] < prior_max[1] and \
            prior_min[2] < theta[2] < prior_max[2] and \
            prior_min[3] < theta[3] < prior_max[3] and \
            prior_min[4] < theta[4] < prior_max[4] and \
            prior_min[5] < theta[5] < prior_max[5]:
                return 0
    
        else:
		return -np.inf

    def lnlike(theta, **kwargs):

    	fake_obs = kwargs['data']
    	fake_obs_icov = kwargs['data_icov']
    	kwargs.pop('data', None)
    	kwargs.pop('data_icov', None)
    	prior_range = kwargs['prior_range']
    	# Likelihood
    	model_obvs = generator(theta, prior_range)
        #print "model=" , model_obvs
        res = fake_obs - model_obvs
        f = 1.
        neg_chisq = -0.5*f*np.sum(np.dot(res , solve(fake_obs_icov , res)))
    	return neg_chi_tot

    lp = lnprior(theta , **kwargs)
    if not np.isfinite(lp):
        return -np.inf
    return lp + lnlike(theta, **kwargs)


def mcmc_mpi(Nwalkers, Nchains, data_dict={'Mr':21}, prior_name = 'first_try'): 
    '''
    Parameters
    -----------
    - Nwalker : 
        Number of walkers
    - Nchains : 
        Number of MCMC chains   
    '''
    #data and covariance matrix
    fake_obs_icov = Data.load_covariance(**data_dict)
    fake_obs = Data.load_data(**data_dict)
        
    # True HOD parameters
    data_hod = Data.load_hod_random_guess(Mr=21)
    Ndim = len(data_hod)

    # Priors
    prior_min, prior_max = PriorRange(prior_name)
    prior_range = np.zeros((len(prior_min),2))
    prior_range[:,0] = prior_min
    prior_range[:,1] = prior_max
    
    # mcmc chain output file 
    chain_file = ''.join([util.mcmc_dir(),'.mcmc_chain.dat'])

    if os.path.isfile(chain_file) and continue_chain:   
        print 'Continuing previous MCMC chain!'
        sample = np.loadtxt(chain_file) 
        Nchain = Niter - (len(sample) / Nwalkers) # Number of chains left to finish 
        if Nchain > 0: 
            pass
        else: 
            raise ValueError
        print Nchain, ' iterations left to finish'

        # Initializing Walkers from the end of the chain 
        pos0 = sample[-Nwalkers:]
    else:
        # new chain 
        f = open(chain_file, 'w')
        f.close()
        Nchain = Niter
         
        # Initializing Walkers
        random_guess = data_hod
        pos0 = np.repeat(random_guess, Nwalkers).reshape(Ndim, Nwalkers).T + \
                         5.e-2 * np.random.randn(Ndim * Nwalkers).reshape(Nwalkers, Ndim)
    # Initializing MPIPool
    pool = MPIPool()
    if not pool.is_master():
        pool.wait()
        sys.exit(0)

    # Initializing the emcee sampler
    hod_kwargs = {
            'prior_range': prior_range, 
            'data': fake_obs, 
            'data_icov': fake_obs_icov, 
            'Mr': data_dict['Mr']
            }
    sampler = emcee.EnsembleSampler(Nwalkers, Ndim, lnPost, pool=pool, kwargs=hod_kwargs)

    # Initializing Walkers 
    for result in sampler.sample(pos0, iterations=Nchain, storechain=False):
        position = result[0]
        #print position
        f = open(chain_file, 'a')
        for k in range(position.shape[0]): 
            output_str = '\t'.join(position[k].astype('str')) + '\n'
            f.write(output_str)
        f.close()

    pool.close()


if __name__=="__main__": 
    generator = MCMC_model(Mr = 21)
    continue_chain = False
    Nwalkers = int(sys.argv[1])
    print 'N walkers = ', Nwalkers
    Niter = int(sys.argv[2])
    print 'N iterations = ', Niter
    mcmc_mpi(Nwalkers, Niter)