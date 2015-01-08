## **Installing Morse**

Sean Trott 

Email: <seantrott@icsi.berkeley.edu>

Link to "compling" directory: <https://github.com/icsi-berkeley/ecg-specializer>

* Should contain following directories: lib, src, and grammars


#### Mac Installation:

The other tutorial for this project (https://github.com/icsi-berkeley/ecg-specializer/blob/master/specializer_tutorial.md) explains how to run the grammar on Command Line, along with the Specializer. It also includes a section for running the Morse simulation, but this is only possible if you’ve installed Morse. Morse is a simulator that uses the Blender graphics engine; it’s been formally tested in Linux, but we run it successfully on Macs - as far as I know, it hasn’t been tested on Windows.

The Morse website conveniently includes instructions (http://www.openrobots.org/morse/doc/1.2/user/installation.html) for installation. The specific process we followed will be explained below, but feel free to use one of the options on the site (we used Homebrew for installation, but there are also manual install options). Additionally, there are certain compatibilities that arose on the Yosemite update. If you don’t have Yosemite, don’t bother reading that section (just read the “installation procedure section”), but if you do, you’ll need to make additional changes.

##### Installation procedure:
1) Install Homebrew (requires Xcode and command line tools): 

```
$ ruby -e "$(curl -fsSL https://raw.github.com/mxcl/homebrew/go)"
```

2) Download Blender (http://www.blender.org/download/). I use a past version of Blender: 2.71, found in the list of versions here: http://download.blender.org/release/. You can install the app wherever you want on the computer (/Applications is a safe bet), just make sure the $MORSE_BLENDER variable points to the executable, found at the path: blender.app/Contents/MacOS/blender

3) Install Python3 using Homebrew. 

Navigate to your /usr/local folder:

```
$ cd /usr/local
```

Check the versions of python3:

```
$ brew versions python3
```

You should get a list of python3 versions. Copy the version you want to use - note that this should be compatible with the Blender version you download (I use python3.4.0 and Blender 2.71, but on Yosemite we found it necessary to use python 3.4.2 and Blender 2.72b). Copy the line corresponding with the version (let’s assume it’s “git checkout fedb343 Library/Formula/python3.rb”), then paste it into Terminal and run “brew install python3”: 

```
$ git checkout fedb343 Library/Formula/python3.rb
$ brew install python3
```

It’s important to note that this should be the only or main version of python3 installed; other versions can cause conflicting compilations for Morse.

3) Install Morse using Homebrew:

```
$ brew tap morse-simulator/morse
```

When I first installed Morse, they hadn’t updated the installation package to the newest Morse version, so you might have to do that yourself. You can check using the VIM editor:

```
$ vi /usr/local/Library/Taps/morse-simulator/homebrew-morse/morse-simulator.rb
```

On line 4 you will see the line:
```
url 'https://github.com/laas/morse.git', :tag => '1.2'
```
Change the tag to ‘1.2.1’ by typing ‘i’, navigating to the correct part of the text and inserting the right numbers. Save your change by pressing ESCAPE, then typing “:wq” in that order. (That will write and quit the file.)

If the tag is already 1.2.1, you shouldn’t need to change it. If it’s 1.2.2, some of the issues in the Yosemite installation will also have been taken care of.

Install pymorse:
```
$ pip3 install pymorse
```

Now you should be ready to install Morse:

```
$ brew install morse-simulator --with-pymorse
```

You can check the installation worked by typing:
```
$ morse check
```

If it runs smoothly, you should be ready to run the robot simulation. If there are errors, check to see what the error message tells you. Common errors we ran into involved:
* Wrong Python version
* $MORSE_BLENDER variable not set
* Wrong Blender version

If you are having issues with the installation, the Morse team is very helpful with answering questions. If I am available, I can also do my best to help with questions.

##### Yosemite Installation:

As mentioned above, there are certain incompatibilities that arise between Morse and the new Yosemite OS for Macs. Some of these may have been addressed with the newest Morse release (1.2.2), but some are not. One issue on Yosemite is that versions of Blender before 2.71 cause a “segmentation fault”. This is problematic because Morse 1.2 requires a version of Blender between 2.62 and 2.7. In order to use Blender versions past 2.7, you’ll need at least Morse 1.2.1 (which bumps the max Blender version to 2.72). See the previous section for updating to Morse 1.2.1 (if you only have 1.2).

###### Problem 1

If you want to use a later version of Blender, such as 2.72b (which is what we used for Yosemite), you can change the “STRICT_MAX_BLENDER_VERSION” variable in the morse initiation file. Navigate in Terminal to:

```
$ cd /usr/local/Cellar/morse-simulator/1.2.1/bin
```
(Depending on the version, you might type “1.2” or “1.2.2” instead of “1.2.1”.)

There should be a file called “morse” in there. Edit it in VIM:
```
$ vi morse
```

Scroll down to the line that reads:
STRICT_MAX_BLENDER_VERSION = “2.72” *
* Could be a separate number.
Change this in the VIM editor to something like “2.73”, if you’re using Blender 2.72b. This is a read-only file, so overwrite the file using “:wq!”. 

This should allow you to use more advanced versions of Blender. 

###### Problem 2

Another problem we ran into was an error that read: “Fatal Python error: PyThreadState_Get: no current thread”. This is due to incompatibilities between Morse and certain Python versions. Part of the issue is that Blender must be compiled with a certain Python3 version, and Morse must be compiled with a certain Python3 version; if those versions are different, Morse raises an error. There are likely multiple ways to deal with this, but the Morse moderators in this thread (https://github.com/morse-simulator/morse/issues/576) suggested a solution that worked for us.

First, make sure the version of Python3 you’ve installed is 3.4.2. If it’s not, uninstall it using “brew uninstall python3” and then reinstall the correct version.

If you had to change your Python3 version, then also uninstall morse:
```
$ brew uninstall morse-simulator
```

Reinstall it once you’ve installed the correct Python3 version.
```
brew install morse-simulator
```

* Note that if you follow these directions from the beginning, you shouldn’t have to uninstall or re-install anything.

Now, you can edit the same “morse” file as before (in Problem 1). Open it up in VIM, and navigate down to a line that reads:
```
########
# “Check python version within blender”
```

Comment out all the lines between “python_version” and the next function (def get_config_file()) using the # comment syntax or the “”” comment syntax for blocks of text. Save the file using “:wq!”. 

This will stop Morse from trying to check the Blender’s python version. After doing this, the simulation ran smoothly on our machines.






