
## Installing Ubuntu

#### Starting installer from DVD

Turn on the computer and tap F12 to get to the boot menu. Select 'Change Boot Mode Settings' and change the mode to 'UEFI Boot Mode, Secure Boot OFF'. This should let us boot to something other than the Windows partition.

Insert the USB into the computer.

When the computer restarts, tap F12 to get to the boot menu, then select the DVD drive (EFI mode).

I then found that the installer just ended up hanging at a blank screen. I needed to Ctrl-Alt-F1 (to get to a console) and then `startx` to get the installer going.


#### Partitioning

SSD:
* 200 MB for the EFI system partition
* `/` partition: 200 GB
* `/var` partition (where the reads will go): rest of SSD

HDD:
* swap partition: 100 GB of HDD
* `/home` for rest of HDD

I used primary partitions for each.

https://askubuntu.com/questions/343268/how-to-use-manual-partitioning-during-installation




## Updates

```
sudo apt-get update
sudo apt-get upgrade
```




## zsh

```
sudo apt install zsh
sudo apt install git
sh -c "$(wget https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh -O -)"
```

Then log out and back in again.




## More apt packages

```
sudo apt install checkinstall
sudo apt install pigz
sudo apt install hdf5-tools
sudo apt install vim
sudo apt install libz-dev
```




## MinKNOW, Guppy and Albacore

```
wget -O- https://mirror.oxfordnanoportal.com/apt/ont-repo.pub | sudo apt-key add -
echo "deb http://mirror.oxfordnanoportal.com/apt xenial-stable non-free" | sudo tee /etc/apt/sources.list.d/nanoporetech.sources.list
sudo apt-get update
sudo apt-get install minknow-nc
sudo apt-get install ont-guppy
```

The MinKNOW install failed to produce an application:
https://community.nanoporetech.com/posts/installing-minknow-on-linu?search_term=minknow%20ubuntu
So I had to launch it by running `/opt/ui/MinKNOW` (then pin to the launcher).

For Albacore I just followed the instructions on the ONT Community site.




## CUDA

Download the CUDA 9.0 deb (local) from NVIDIA's site. Version 9.2 is no good, as it's not compatible with the driver version that Guppy needs.

```
sudo dpkg -i cuda-repo-ubuntu1604-9-0-local_9.0.176-1_amd64.deb
sudo apt-key add /var/cuda-repo-9.0-local/7fa2af80.pub
sudo apt update
sudo apt install cuda-toolkit-9.0  # don't just install cuda or else that will overwrite the drivers
```




## cuDNN

https://developer.nvidia.com/rdp/form/cudnn-download-survey

Log in with my NVIDIA developer credentials. Download the cuDNN library compatible with CUDA 9.0 (I got the runtime deb for Ubuntu 16.04) and install.

I then added these to my `.zshrc` file:
```
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/extras/CUPTI/lib64
export PATH=$PATH:/usr/local/cuda-9.0/bin
```




## Mounting storage server

First make sure SSH keys are set up:

```
ssh-keygen
ssh-copy-id -p 4321 wickr@eminor.mdhs.unimelb.edu.au
```

Then add a line to `/etc/fstab`:

```
sshfs#wickr@eminor.mdhs.unimelb.edu.au:/data /mnt/eminor     fuse defaults,delay_connect,port=4321,allow_other,reconnect,IdentityFile=/home/holt-ont/.ssh/id_rsa,idmap=user 0 2
```




## Tensorflow

https://www.tensorflow.org/install/install_linux

I used the pre-build pip package (tensorflow-gpu) which worked nicely.




## Other Python packages

```
sudo pip3 install keras
sudo pip3 install edlib
sudo pip3 install noise
sudo pip3 install h5py
sudo pip3 install ont-tombo
sudo pip3 install pandas
```




## Other tools

#### SublimeText

```
wget -qO - https://download.sublimetext.com/sublimehq-pub.gpg | sudo apt-key add -
echo "deb https://download.sublimetext.com/ apt/stable/" | sudo tee /etc/apt/sources.list.d/sublime-text.list
sudo apt-get update
sudo apt-get install sublime-text
```


#### Porechop

```
cd ~
git clone https://github.com/rrwick/Porechop.git
cd Porechop
python3 setup.py install
porechop -h
```


#### Deepbinner

```
cd ~
git clone https://github.com/rrwick/Deepbinner.git
cd Deepbinner
python3 setup.py install
deepbinner -h
```
