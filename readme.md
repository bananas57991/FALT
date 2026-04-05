# For these files to work:
   ## For linux users:

1. Download the project files
2. run ghost_api.py
3. open a secondary terminal and run ```cd /tmp && python3 -m http.server 8000```
4. open firefox
5. in url bar type ```about:debugging#/runtime/this-firefox```
6. click ```Load Temporary Add-on```
7. navigate to the folder that holds the plugin folder and select only ```manifest.json``` and then open.
8. Back to firefox

   # what this does:
  ## When you receive a falt link (usually looks something like this: falt://+BkQtdhE.fairviewgroupinc.com) you would put this part of the string into the plugin ```+BkQtdhE.fairviewgroupinc.com```.  
 ## It then decodes the link and provides the IP address, port, domain to ghost_api.py to resolve.  The terminals then fetch all the html and provide a file for the plugin to read from and open a new tab with the resulting data.

  ### This set is currently working for IPv4 ssl certified sites (sites that use 443 as the port)


# Alternative methods to achieve the same outcome:
 ## Alter Host files:
 1) Decode the link you were given using the faltlink_dual_decoder_v2.py
 2) go to your hosts file found at  /etc/hosts
 3) add the ip and domain as an entry and save.
 4) go to browser of choice and input the domain

 ## ModHeader
 1) in your browser go to the extensions store and look for ModHeader & get it
 2) decode the falt link you were given using the faltlink_dual_decoder_v2.py
 3) input the ip and domain into the ModHeader plugin on your browser
 4) visit the domain like you would normally.
  
  * For experimental untested versions see the ```BETA``` folder in the project files
  * Questions can be directed to ```fairviewgroupincor@gmail.com```

  * last update : Sunday April 5, 2026 00:01:00 am PST (UTC-7:00)
