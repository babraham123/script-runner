# Setup Instructions

Run through these instructions and then try to load the example notebooks presented in the repo. All examples borrowed from the [IPython Gallery Project](https://github.com/ipython/ipython/wiki/A-gallery-of-interesting-IPython-Notebooks).

```bash
cd ~
sudo apt-get install -y nginx gunicorn
sudo easy_install pip
sudo pip install "ipython==3.2.1"
sudo pip install runipy
sudo pip install Flask
mkdir notebooks
```

ipython notebook --no-browser --ip=68.67.158.95 --pylab inline --port=8003 --notebook-dir=/home/babraham/notebooks --script

ipython notebook --no-browser --port=8003 --notebook-dir=/Users/babraham/Desktop/projects/script-runner/notebooks

%matplotlib inline
