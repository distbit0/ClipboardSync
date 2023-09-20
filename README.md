Works over 4g and with a VPN. Free. No account required. Uses https://ntfy.sh. Can be self hosted.

Keyboard shortcut mappings:

#### Send clipboard contents
`ctrl + super + c` ===> `/bin/python3 /PATH/TO/THIS/REPOSITORY/send.py CHANNEL_ID`

#### Send currently selected text
`ctrl + super + s` ===> `/bin/python3 /PATH/TO/THIS/REPOSITORY/send.py CHANNEL_ID --selected`

#### cronjob for receiving messages
`@reboot ntfy sub DIFFERENT_CHANNEL_ID /PATH/TO/THIS/REPOSITORY/receive.sh`

(use one channel to send and one to receive so that you do not receive messages you send on the same device)


Install ntfy on desktop:

https://docs.ntfy.sh/install/

Install ntfy on mobile:

https://docs.ntfy.sh/


#### Guide for automating opening handling of messages on androis (e.g. opening links or copying to clipboard)
https://docs.ntfy.sh/subscribe/phone/

#### Guide for creating share target on android which sends text to ntfy api
http://forum.joaoapps.com/index.php?resources/creating-autoshare-commands-for-your-share-menus-a-detailed-tutorial.335/