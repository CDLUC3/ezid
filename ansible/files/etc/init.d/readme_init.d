~/etc/init.d/README
===================

We now use systemctl to manage the ezid httpd service:

sudo systemctl status ezid
sudo systemctl start ezid
sudo systemctl stop ezid
sudo systemctl restart ezid


other useful commands:

systemctl cat ezid
journalctl -u ezid
journalctl -u ezid -S today
