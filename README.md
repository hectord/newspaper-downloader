# NewspaperDownloader

ND is a web site that unifies the way you download your newspapers. It is made up of a worker, downlading every new issue as it comes out, and a web server to download all of them in one click.

I have developed two plugins to download my (swiss) newspapers:
 * 24 heures
 * Le Temps

You can use them if you have a valid subscription. Otherwise you can develop a new plugin to download your own newspaper on the platform.

Please, don't ask me my credentials to download my newspapers. I use this application to promote newspapers not to steal them.

## Installation

If you have a valid subscription and the corresponding plugin to download it, you can set up your own server.

 1. Set your credentials in the file corresponding to the newspaper (those I have already developed are in "available_plugins/<< your newspaper >>.py")
 2. Copy the plugin in the active plugin directory (in "nd/plugins/")
 3. Launch the downloader on your server using:
       > python main.py
 4. Set up the credentials to access your newspaper on the web server using:
       > python manager_user.py -c << your user name >>
 5. Launch the webserver to see your newspaper issues:
       > python webserver.py

Every morning, the new issues will be downloaded. If it fails to download one of them, the application retries a few hours later. If you want to receive your newspapers by email you can use the option "--email" when launching the downloader.

If you want to be aware of any crash of the downloader, set your email in "downloader.py".

## Requirements

I use this application with python 3.4. It requires ImageMagick to create the thumbnails on the web site. If you don't have "convert" in your path, please add it before launching the downloader.

Depending on the plugin, you could need other applications. See the plugin's header for more information.

## Contribution

If you want to develop new plugins for your subscriptions, you can take a look at the existing plugins in "available_plugins/" or in "nd/newspaper_api.py" to understand which class you must extend to create your own plugin.

If you want to add new functionalitites, send me a pull request! I would be happy to work with other people on this project.

