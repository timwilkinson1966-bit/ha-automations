# ha-automations
A collection of tested Home Assistant automations for presence, lighting, climate, and security



# Motion Camera Popup (iPhone + Browser)

A simple Home Assistant blueprint that sends a camera notification to an iPhone or iPad when motion is detected, and can also optionally open a Browser Mod popup on a dashboard or tablet.

This is still an early version and is fairly basic, but it is working and should be useful as a starting point. I am very much a beginner when it comes to coding and building blueprints, so this project has mainly been a learning exercise that I wanted to share in case it helps others.

## What it does

This blueprint allows you to:

- trigger from a motion sensor
- send a push notification to an iPhone or iPad
- include the selected camera view in that notification
- optionally open a Browser Mod popup on a browser or tablet dashboard

A typical use would be:

- front door motion is detected
- Home Assistant sends a notification to your phone or iPad
- the selected front door camera image is shown in the notification
- optionally, a dashboard can also show a popup camera view

## Features

- motion-triggered camera notifications
- works with iPhone or iPad mobile app notification services
- optional Browser Mod popup support
- simple inputs and straightforward setup
- useful as a basic starting point for camera alert automations

## Requirements

Before using this blueprint, you should already have:

- a working motion sensor in Home Assistant
- a working camera entity in Home Assistant
- the Home Assistant mobile app installed on your iPhone or iPad
- a valid mobile app notify service, such as:
  - `notify.mobile_app_your_iphone`
  - `notify.mobile_app_your_ipad`
- Browser Mod installed if you want to use the popup feature

## Blueprint inputs

### Motion Sensor
The binary sensor that will trigger the automation when motion is detected.

### Camera
The camera entity that will be attached to the notification and optionally shown in the popup.

### iOS Device
The Home Assistant mobile app notify service for the device you want to receive the notification.

Examples:

- `notify.mobile_app_tim_ipad`
- `notify.mobile_app_tw_iphone_16_max_pro`

### Browser ID (optional)
The Browser Mod `browser_id` for a dashboard or tablet if you want the popup feature.

Leave this blank if you only want a mobile notification.

### Notification Message
The message text to send with the notification.

## How to import

Import this blueprint into Home Assistant using this URL:

`https://github.com/timwilkinson1966-bit/ha-automations/blob/main/blueprints/automation/timwilkinson1966-bit/motion_camera_popup_iphone_browser.yaml`

In Home Assistant:

1. Go to **Settings**
2. Open **Automations & scenes**
3. Open **Blueprints**
4. Select **Import blueprint**
5. Paste in the GitHub URL above

## How to use

1. Import the blueprint
2. Create a new automation from it
3. Select the motion sensor
4. Select the camera
5. Enter your iPhone or iPad notify service
6. Optionally enter a Browser Mod browser ID
7. Enter your notification message
8. Save the automation
9. Test it properly

## Example setup

### Front door to iPhone
- Motion Sensor: front door motion sensor
- Camera: front door camera
- iOS Device: `notify.mobile_app_tw_iphone_16_max_pro`
- Browser ID: blank
- Notification Message: `Front Door Motion detected!`

### Front door to iPad
- Motion Sensor: front door motion sensor
- Camera: front door camera
- iOS Device: `notify.mobile_app_tim_ipad`
- Browser ID: blank
- Notification Message: `Front Door Motion detected!`

## Notes

- If Browser ID is left blank, the blueprint will only send the mobile notification.
- If Browser Mod is used, it can also open a popup showing the selected camera.
- This blueprint is aimed at simple camera alert use, not advanced event handling.
- Some setups may need adjustment depending on device behaviour, notification settings, or camera integrations.

## Current limitations

This is still an early-stage project, so there are a few limitations:

- basic functionality only
- limited customisation
- no advanced cooldown or anti-spam handling yet
- no advanced notification tap actions yet
- may need refinement for different user setups

## Future improvements

When time allows, I would like to improve it further with things such as:

- cooldown options
- better anti-spam handling
- more flexible camera options
- improved live view handling
- cleaner and more polished blueprint structure
- better support notes for different devices

## Beginner project note

I am still very new to coding, YAML, and Home Assistant blueprint creation. This blueprint has been built through trial, error, testing, and gradual improvement. It may not be perfect, but it is a working starting point and hopefully something I can continue improving over time.

## Feedback

Constructive feedback is welcome. If you spot a cleaner way of doing something, or a useful improvement, that would be helpful.

## Disclaimer

Please test this properly in your own setup before relying on it for important security or safety notifications.
