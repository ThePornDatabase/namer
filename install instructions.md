Install Instructions
=================

To start off with namer there are 3 main ways to install it:

* Windows
* Docker
* Unraid

Windows can be an easy setup for the uninitiated and has a pretty good webui that can take care of you in most ways. Docker/Unraid are very strong if you have a little bit of knowhow as they are just more reliable and cause less problems. I'll start with windows and work down the list with installation instructions for each.

Windows
-----------------

To start off with windows you only really need to manually install one thing and that's python. Everything else will be downloaded for you once you do you install in cmd promt.

**Step 1:** Install the latest version of python from [here.](https://www.python.org/downloads) When you do this install make sure you tick the **Add Python to path**. It makes your life a lot easier and you won't have to manually do it in the future.

**Step 2:** With python now installed you can now download Namer through CMD. This is pretty easily done with a quick command. Open your CMD by typing CMD in your search bar and then type: **pip install namer**.  This is going to download and install all the packages that namer needs to run correctly.

**Step 3:** Now that namer is installed you can setup your config. Go ahead and get a copy of a default config page from Github [here](https://github.com/ThePornDatabase/namer/blob/main/namer/namer.cfg.default). You can copy it and paste it into your own document or download it straight from github, the option is yours. Once you have it copied or downloaded, go ahead and place it in your install location. The default location that namers uses is **C:/Users/YOURUSER**. With it placed in the correct folder go ahead and rename the file to **.namer.cfg**. Make sure that you add the period to the beginning of file or it will not be detected.

**Step 4:** Now that you have the default config, you have to set it up correctly. I'm not going to go into detail about every setting as they are mostly labeled, i'll just do the ones to get you running. You are going to need to get an API key for namer to talk to TPDB.

To do that go [here](https://metadataapi.net) and make an account if you haven't already. Once you do go into your profile and create an API key. Call it whatever you want and then copy that key into the config in the **porndb_token** section.

Scroll down untill you see the **Watchdog** section. This is where we are going to setup your directories for your folders that namer will look for. It's super important that these are named correctly and **NOT INSIDE ONE ANOTHER**. Putting folders inside each other could result in unexpected errors and outputs.

Namer uses 4 main directories:

* **Watch:** This is where namer looks for new files. When your new scenes are dropped in here namer will detect it and go to work.

* **Work:** This is where namer moves your new scene to so it can do the work scanning and renaming.

* **Failed:** This is where namer moves your files to if it failes to find a match and will automatically try again in 24 hours, unless settings are change to do it earlier.

* **Dest:** This is where namer will place the final file after it has been scanned and renamed.

These folders are important and all 4 need to be accessible for namer to work correctly.

My recommendation for folder structure is as following. Make a new folder and call it whatever you want, for this example I will use **Namer** and place it on my  C: drive. Inside that folder make 3 new folders, naming one **work**, one **failed** and one **dest**. Now that you have all the folders, head back to the config and place the correct directory next to each setting.

* watch_dir = C:/Namer/watch
* work_dir = C:/Namer/work
* failed_dir = C:/Namer/failed

Now your dest_dir directory can be whatever you want. Just DON'T PLACE IT INSIDE ANOTHER NAMER FOLDER. It can cause errors and problems that you won't like.

Now that that is done the very basic functionally of namer is complete and you can run a command in CMD and let it go to work.  You can run **"python -m namer watchdog"** and that will activate watchdog and it will start automatically scanning and renaming files in your watch folder then move them to your destination folder.

**Step 5:** Most people, like I, don't like command line stuff so we have a webUI that can be used to make life a little easier for you. Firstly you have to active it in your config, search for the **web = False** in your config and set it to **true**. The default port is essentially your local host and port is 6980. You can change this if you need to and know what to do. Otherwise just go to your browser and type **localhost:6980**. This should bring up the webui where you can manually search and match your files. Namer will only show files that appear in your failed_dir. If you want to do everything manually in the UI, make sure your files are in the failed_dir. If you want namer to do most of the work, place them in watch_dir, let namer match, and then you can manually match anything that Namer can't find.

After these steps you are pretty much setup. There are a lot more settings you can play with but, as I said earlier, they are marked and you can play with them if you need to.

Before you start going crazy and slapping files everywhere:

Namer uses a **STUDIO-DATE-SCENE** format. Essentially this means your folders need to be named that way or namer will not match your files and you will need to do it manually all the time.

Unraid
----------------

Linux systems are more complicated than windows systems but can be more stable and less problimatic as namer mostly runs passivly in the background. This isn't going to be an UNRAID tutorial and i'm going to take certain liberties hoping that you already know how it works.

**Step 1:** Go to your docker tab then click add container down below. I'll put a example template below, the names can be somewhat interchangable but you have to remember them and use your names accordingly.

* Name: namer
* Repository: ghcr.io/theporndatabase/namer:latest

After these are filled in you want to go ahead and add some paths for your media, config, and ports if you plan on using the web. Scroll down and click on **Add another Path, Port, Variable, Label or Device**. While in here make it as such.

* Config Type: Path
* Name: config
* Container path: /config
* Host Path: /mnt/user/appdata/namer (This is important as it's where your namer.cfg is going to get placed.)
* Default value : /config

Now we're going to do that again but create for where your media and namer working folders are going to live. You can make one for your work folders and then another to where your media lives but that's up to your personal preference.

* Config Type: Path
* Name: media
* Container path: /media
* Host Path : /mnt/user/media (This is the top folder that all my work folders are in and then another subfolder where my media lives. Essentially when namer looks in /media it can see all 4 folders that namer uses)
* Default Value : /media

After that we can go ahead and link in our port for the webUI. You can use whatever port you see fit just make sure to update it on your namer.cfg

* Config Type: Port
* Name: port
* Container port: 6980 (or whatever you want it to be)
* Host port: 6980
* Connection Type: TCP

We also need to make some PUID and PUIG ones for your perms. It's exactly the same as above but you use variable instead of path.

So, all of these are essentially translations between namer and unraid. When you type **/config** into namer it will tell unraid and unraid will look in **/mnt/user/appdata/namer**. This also applies to all the other ones we made too.

So go ahead and hit **Apply** and let unraid do it's thing. Once you do that namer will be installed but it won't run as since your config isn't where it needs to be.

**Step 2:** Go ahead and move your namer.cfg into your **/config** folder. You can do that via windows SMB or something of that sort. You can also learn how to create your config above in the Windows section. The only main difference is going to be your paths and the fact that, in unraid, your **namer.cfg** doesn't need the period at the beginning. If you put your folders in side of /media then your config should look like this:

* watch_dir = /media/watch
* work_dir = /media/work
* failed_dir = /media/failed
* dest_dir = /media/DESTINATION

You can go ahead and set your webui and webui port if you wanted acess to that as well.

**Step 3:** You're essentally done, so you can go ahead and boot up namer. To acess the webui you can go ahead and use your `serverip:6980`. Now you can start putting files in your watch folder and let namer go to work.
