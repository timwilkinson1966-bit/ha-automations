# ha-automations
A collection of tested Home Assistant automations for presence, lighting, climate, and security



Motion Camera Popup (iPhone + Browser)

A simple Home Assistant blueprint that sends a camera notification to a mobile device when motion is detected, and can also open a Browser Mod popup if required.

This is an early-stage blueprint and is still fairly basic. The main aim at the moment is to provide a straightforward way to link a motion sensor to a camera notification without needing to build the automation from scratch each time.

I am still very new to coding and blueprint creation, so this has been put together as a learning project. It may not yet cover every use case, and there will almost certainly be cleaner or more advanced ways to do some parts of it. That said, it is working and should be useful as a starting point for others who want something simple and practical.




What it does

This blueprint allows you to:

* trigger from a motion sensor
* send a push notification to a mobile device
* include the selected camera view in that notification
* optionally open a Browser Mod popup on a dashboard or tablet

It is mainly intended for quick camera alerts, such as a front door motion event sending the relevant camera view to your phone.




What you need

Before using it, you should already have:

* a working motion sensor in Home Assistant
* a working camera entity in Home Assistant
* the Home Assistant mobile app set up on your phone or tablet
* Browser Mod installed if you want to use the browser popup option



How to use it

1. Import the blueprint into Home Assistant.
2. Create a new automation from the blueprint.
3. Select the motion sensor you want to use.
4. Select the camera you want attached to the notification.
5. Choose the mobile notification action for your device.
6. Optionally enter a Browser Mod browser ID if you want a popup on a dashboard or tablet.
7. Set your preferred notification message.
8. Save the automation and test it.



Intended use example

A typical example would be:

* front door motion is detected
* Home Assistant sends a push notification to your iPhone
* the front door camera image is shown in the notification
* optionally, a dashboard tablet can also open a live popup view



Current limitations

At this stage, this blueprint is still quite simple.

Known limitations include:

* limited customisation
* no advanced cooldown handling yet
* basic notification logic only
* may need refining for different devices or unusual setups
* Browser Mod use is optional and not the main focus



Future improvements

Given more time, I would like to improve it further by adding things such as:

* better cooldown and anti-spam handling
* more polished input selection
* clearer support for Android and iPhone differences
* better handling for live camera view and tap actions
* more flexible notification options
* cleaner coding and overall structure

  


Feedback

As this is a beginner project, constructive feedback is welcome. If something does not work properly in your setup, or you have a better way of doing part of it, that would be useful to know.


Disclaimer

This blueprint is shared in good faith as a working early version. Please test it properly in your own setup before relying on it for important security or safety notifications.
