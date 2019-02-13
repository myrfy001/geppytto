### Geppytto is a headless chrome cluster proxy, it warps a cluster of browsers into two kinds of virtual browsers:
* Free browser: A browser that has a single incognito browser context, a random browser process on a random cluster node will be selected to serve this incognito context, and when disconnected, all user data will be cleared.
* Named browser: A browser that has full function as a real browser process, and it lives on a fixed cluster node, user data will be kept when disconnected and you can connect back any time you want.


### How does it work?

The architecture of Geppytto is showing below

![](https://docs.google.com/drawings/d/e/2PACX-1vTN-juJUItgNgLNjUmdWXJKdFEIRIxv813XBkn68cjXr416wn8g2_mflRvqMMF0vr51fDeC2KexNv3E/pub?w=942&amp;h=414)

The Geppytto has two main component:
* Geppytto: Each node runs a single `Geppytto` process, it accepts connections and launch children `Agent` processes
* Agent: Each `Agent` process will launch one Browser, and keep an eye on that browser.

The main workflow is:



### Why it's call Gep*py*tto?
* Because Pu(y)ppetter controls browsers
* Because Pinocchio is a puppet
* Because Geppetto is Pinocchio's father
* And because Geppytto is written in Python