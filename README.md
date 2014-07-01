Basics

Script Runner is a python web application that can run arbitrary python code. This code is pulled from ipython notebooks, and is rendered as astatic html page. The general idea was to recreate an ipython notebook server, that is read-only and allows a set number of input parameters. The code is written with Tornado, using their native templating and web serving capabilities. 

Setup and Deployment

The script has certain dependencies that make setup and deployment a little tricky.

1. To run native python code, the app creates a new ipython KernelManager object. The object in turn spans a new child process and uses zmq messages to communicate with the new process. Because of this, the app cannot run on Apache child processes. Right now, I'm running the app out of my home directory using Tornado's with a set number of processes. I believe a proper deployment would be to run it under /root as a daemonized process.

2. The rest of the issues are relatively easy to solve. I have hard coded a lot of relative paths, so within the project folder you cannot move any of the folders. For example, I use 'ipython nbconvert' to render the ipython notebooks as html pages. IPython depends on a configuration folder called ".ipython". 
In addition, a lot of scripts use a convenient database connector library called Link. Link depends on a configuration file saved under ".link/link.confg".
A lot of files go into "public/static/", which maps to "/static" on the public website.
UI templates go in "templates/"
All ipython notebooks go into "scripts/"

3. The third issue is pandoc. Nbconbvert depends on pandoc to convert specific types of ipython notebooks, usually ones with charts and graphs. Pandoc is a document converter written in haskell, and can be installed with the cabal package manager. Remember to install pandoc to /root and to add the cabal bin to the PATH (further instructions﻿).

4. Every time someone runs a script, the app generates a unique html file and a unique csv file (if the script has download options) in "public/static/". I have a daily cron job to delete all of the temporary files that accumulate by the end of the day.

