from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
import neyman.models as nm
import edward as ed
import numpy as np

ds = tf.contrib.distributions

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

def merge(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z

def create_1D_toy_model():

  mu = nm.Uniform(low=0.0, high=5.0, name="mu")

  s_exp = tf.convert_to_tensor(20., name="s_exp")

  c0_norm = nm.Normal(loc=200.,scale=20., name="c0_norm")
  c1_norm = nm.Normal(loc=200.,scale=20., name="c1_norm")
  
  c0_ori = ds.Normal(loc=-2.0, scale=0.75, name="c0_ori")
  c1_ori = ds.Normal(loc=0.0, scale=2.0, name="c1_ori")
  s_ds = ds.Normal(loc=1.0, scale=0.5, name="s_pdf")
  
  c0_shift = nm.Normal(loc=0.0,scale=0.25, name="c0_shift")
  c0_aff = ds.bijectors.Affine(shift=c0_shift, name="c0_aff")
  c0_transformed = ds.TransformedDistribution(distribution=c0_ori,
                                              bijector=c0_aff,
                                              name="c0_transformed")
  components = [
      c0_transformed,   # c0 background
      c1_ori,            # c1 background
      s_ds              # s (bump/signal)
  ]
  
  counts = tf.stack([c0_norm, c1_norm, mu*s_exp])
  tot_exp = tf.reduce_sum(counts, axis=-1)
  probs = counts/tot_exp
  n_ev = nm.Poisson(rate=tot_exp, name="n_ev")
  
  cat = ds.Categorical(probs=probs)
  
  mixture = nm.Mixture(components=components, cat=cat, name="mixture")

  rvs_dict = AttrDict({ "mu" : mu,
                        "c0_norm" : c0_norm,
                        "c1_norm" : c1_norm,
                        "c0_shift" : c0_shift,
                        "n_ev" : n_ev,
                        "mixture" : mixture })

  return rvs_dict 

def main(_):

  ed.set_seed(19)

  n_train_evs = 100000
  rvs = create_1D_toy_model()

  fixed_nuis = { rvs.c0_norm : 200.,
                 rvs.c1_norm : 200.,
                 rvs.c0_shift : 0.}

  with tf.Session() as sess:
    bkg_nom_train = sess.run(rvs.mixture.sample(n_train_evs),
                             merge(fixed_nuis, {rvs.mu: 0.}))
    sig_nom_train = sess.run(rvs.mixture.components[2].sample(n_train_evs),
                             fixed_nuis)

  bkg_nom_train = bkg_nom_train[:,np.newaxis]
  sig_nom_train = sig_nom_train[:,np.newaxis]

  np.savez("toy_1D_ind_train_samples.npz",
           sig=sig_nom_train, bkg=bkg_nom_train)
  
  X_sample = np.vstack([bkg_nom_train,sig_nom_train])
  y_sample = np.vstack([np.zeros(bkg_nom_train.shape, dtype=np.int32),
                       np.ones(sig_nom_train.shape, dtype=np.int32)])

  np.savez("toy_1D_cat_train_samples.npz",
           X=X_sample, y=y_sample)

if __name__=="__main__":
  tf.app.run()

