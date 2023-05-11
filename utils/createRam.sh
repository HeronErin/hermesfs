
sudo mkdir /mnt/ramfs rcv
sudo mount -t ramfs -o size=5g,maxsize=5g ramfs /mnt/ramfs
sudo chown -R $(whoami):$(whoami) /mnt/ramfs

sudo truncate -s 5G /mnt/ramfs/ramdisk.img
sudo mkfs.ext4 /mnt/ramfs/ramdisk.img
sudo mount /mnt/ramfs/ramdisk.img rcv
sudo chown -R $(whoami):$(whoami) rcv
