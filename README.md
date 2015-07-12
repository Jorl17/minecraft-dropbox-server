# minecraft-dropbox-server
Ever tried running a **Minecraft server** together with your friends using Dropbox or another similar service? This tool is just for you!

**minecraft-dropbox-server** is a simple python 3 script with the purpose of easing the whole process of running a "distributed" minecraft server. Instead of running the minecraft server and taking all precautions to check that nobody else is doing it, simply make sure everyone uses the **minecraft-dropbox-server** utility! Say you have a dropbox folder named "Minecraft Server Friends", then all your friends and you need to do is:

	mc-dbox-server -n minecraft-server

Install instructions can be found [here](#how-do-i-installuninstall-it).

With only these options, **minecraft-dropbox-server** will check if a server is already running and tell you its IP (it will auto-detect your dropbox folder). If there is no server, it will start its own and make sure everyone else knows its running. There are many tunable options, and you can even use a central server for some additional bookkeeping (in case you there is some problem with the database backend...it's really a niche option)

Table of Contents
=================

  * [How does it work?](#how-does-it-work)
  * [Why are there two applications? And what are they?](#why-are-there-two-applications-and-what-are-they)
  * [How do I install/uninstall it?](#how-do-i-installuninstall-it)
    * [Examples:](#examples)
      * [Install](#install)
      * [Install to /usr/local prefix](#install-to-usrlocal-prefix)
      * [Uninstall](#uninstall)
      * [Uninstall from /usr/local prefix](#uninstall-from-usrlocal-prefix)
  * [If mc-dbox-server executes my Minecraft Server, can I change the JVM arguments? What are the defaults?](#if-mc-dbox-server-executes-my-minecraft-server-can-i-change-the-jvm-arguments-what-are-the-defaults)
  * [Can I change the IP that mc-dbox-server reports?](#can-i-change-the-ip-that-mc-dbox-server-reports)
  * [Can I use multiple instances of mc-dbox-server at the same time?](#can-i-use-multiple-instances-of-mc-dbox-server-at-the-same-time)
  * [What happens if the server crashes? What if the server is stopped but mc-dbox-server thinks it's not?](#what-happens-if-the-server-crashes-what-if-the-server-is-stopped-but-mc-dbox-server-thinks-its-not)
  * [What are the secret key options for?](#what-are-the-secret-key-options-for)
  * [Are you able to automatically launch Minecraft or add the current IP to its list?](#are-you-able-to-automatically-launch-minecraft-or-add-the-current-ip-to-its-list)
  * [Full option list](#full-option-list)

Created by [gh-md-toc](https://github.com/ekalinin/github-markdown-toc)

# How does it work?
**minecraft-dropbox-server** is very simple. It creates an additional file in your server, named `mc_dropbox_server_status.txt`. In this file, it **logs the IP of the current host** (it deletes the file if there is no host). All the rest is just wrapper code to start and stop the server at the right time and allow you to supply many flags, such as the JVM arguments you want, etc.

There is also the possibility of using a centralized server just for the bookkeeping data. That way, even if you can't host your own full-blown server, you might be able to host just a tiny webserver that indicates where the game is currently hosted. The idea would be that this server would be more reliable than Dropbox (it handles only one request at a time, thus avoiding concurrency issues). However, *in its current version*, if the Dropbox and the server have a mismatch, the Dropbox version is preferred. So the server itself isn't really doing much at the moment, but that will probably change in the future, as the code matures. This is also why the current install script doesn't even install the server.

# Why are there two applications? And what are they?

**mc-dbox-server** is the main application that you'll always use when you want to start or join a server. Most people will want to run this with the `-n`,`--server-name` or `-p`,`-path`option (and possibly `-d`,`--dropbox-path`).

**mc-dbox-central-server** is an optional simple web-server with a REST-based API that can be used as an alternative to Dropbox, to further avoid conflicts. This is described in more detail [in the previous question](#how-does-it-work). You'll probably never need it, but that's why **mc-dbox-server** has the **optional** `-s`,`--server-address` and `-k`,`--server-key` flags.

# How do I install/uninstall it?
 Just clone the repository and run ``install.sh``, or ``uninstall.sh`` to remove it. It will install to /usr/bin, but you can change this by passing your desired prefix to install.sh, as an argument. This will install the **mc-dbox-server** application and make it available for you to run.

##Examples:
### Install
    git clone https://github.com/Jorl17/minecraft-dropbox-server
    cd NowCrawling
    chmod +x install.sh uninstall.sh
    sudo ./install.sh
### Install to /usr/local prefix
    git clone https://github.com/Jorl17/minecraft-dropbox-server
    cd NowCrawling
    chmod +x install.sh uninstall.sh
    sudo ./install.sh /usr/local
### Uninstall 
    ./uninstall.sh
### Uninstall from /usr/local prefix
    ./uninstall.sh /usr/local

# If mc-dbox-server executes my Minecraft Server, can I change the JVM arguments? What are the defaults?
You can, it's easy! Just use the `-j`, `--jvm-options`flag. The defaults are `-Xmx3G -Xms2G` and you probably ought to change them.

# Can I change the IP that mc-dbox-server reports?
Sure. Use `-i`,`--ip`to set the IP you want it to report. By default, **minecraft-dropbox-server** will auto-detect your public IP. However, it makes sense that you'd want to change it (e.g. if you'd like to report some LAN/VPN-based IP)

# Can I use multiple instances of mc-dbox-server at the same time?
Absolutely! It doesn't matter if you're the host of one, both or neither. **minecraft-dropbox-server** stores its files in a per-app folder, ensuring it all works straight out of the box

# What happens if the server crashes? What if the server is stopped but mc-dbox-server thinks it's not?
If the server itself crashes, then **minecraft-dropbox-server** will detect this and ensure that you are no longer reported as a host. However, if the computer or **minecraft-dropbox-server** itself crashes, the file is left hanging. This could be overcome by periodically updating the file and checking the date, or using the centralized server, but a more simple solution (and probably adequate, since this is for a small group of friends) is to use the **`-c`,`--clear` option, which completely erases the current host information**. Use this with care!

# What are the secret key options for?

Those are for using together with the **mc-dbox-central-server** application, as explained [here](#why-are-there-two-applications-and-what-are-they). You can safely ignore them.

# Are you able to automatically launch Minecraft or add the current IP to its list?

Not at the moment. Maybe in the future something can be arranged!

# Full option list

```
Usage: mc-dbox-server [options]

Options:
  -h, --help            show this help message and exit
  -s SERVER_ADDRESS, --server=SERVER_ADDRESS
                        Set the remote/central server address (default:
                        http://a.server.com:9000; default: None). If no remote
                        server is supplied, only Dropbox backend will be used.
  -k SECRET_KEY, --secret-key=SECRET_KEY
                        Set the secret key.
  -d DROPBOX_PATH, --dropbox-path=DROPBOX_PATH
                        Manually set the path to the Dropbox base folder (by
                        default, it will be auto-detected)
  -n SERVER_NAME, --name=SERVER_NAME
                        Set the server name. This should match the shared
                        folder in Dropbox. E.g., if server is named DEI, then
                        a folder with that name (and with the jar in it)
                        should be at the root of your Dropbox folder.
  -p SERVER_PATH, --path=SERVER_PATH
                        Manually supply the full path to the server, bypassing
                        dropbox altogether. Cannot use -p with -d and -n.
  -j JAR_NAME, --jar=JAR_NAME
                        Server jar name. By default, the first jar found in
                        the server folder will be used.
  -o JVM_OPTIONS, --jvm-options=JVM_OPTIONS
                        JVM options to use when starting the server (Default:
                        "-Xmx3G -Xms2G")
  -i IP, --ip=IP        Set the IP to report in case a server is started. By
                        default, the public facing IP is auto-detected.
  -c, --clear           Clear the saved state of the current server session.
                        USE WITH CARE. This notifies everyone that the server
                        isn't actually running. If it _is_ running, it is a
                        very bad idea to do this. Use only after a system
                        crash or similar accident.

```