# bbb-network-cam-integration
Prototype to integrate network cameras in BigBlueButton

# Installation:

## Create VM

Create new VM on `vm.elan.codes` with user `bbb-cam`. Add audio device (`ich9-intel-hda`, `SPICE`).

## Clone repository

```
git clone https://github.com/elan-ev/bbb-network-cam-integration.git
```

## Install necessary packages

```
sudo apt install make gcc python3-pip sysstat ffmpeg v4l-utils alsa-base alsa-utils pavucontrol

sudo apt-get -f install && sudo apt-get -y autoremove && sudo apt-get autoclean && sudo apt-get clean && sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

sudo chown -R $USER:$USER $HOME/

wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

sudo apt install ./google-chrome-stable_current_amd64.deb

cd bbb-network-cam-integration

pip3 install -r requirements.txt
```

## Install v4l2loopback module

```
cd ~

git clone https://github.com/umlaeute/v4l2loopback.git

cd v4l2loopback

make

sudo make install

sudo depmod -a
```

## Assign root right 

```
sudo usermod -aG video $USER

sudo usermod -aG root $USER
```

## Allow using sudo without password
```
sudo visudo

#append the following line to the file:
bbb-cam ALL=(ALL) NOPASSWD:ALL
```

## Reboot to finalize changes

```
sudo reboot
```
