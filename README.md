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