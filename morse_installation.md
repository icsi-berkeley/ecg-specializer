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


