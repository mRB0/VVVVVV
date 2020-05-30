This is the source code to VVVVVV, version 2.0+. For more context about this release, see the [announcement](http://distractionware.com/blog/2020/01/vvvvvv-is-now-open-source/) on Terry's blog!

License
-------
VVVVVV's source code is made available under a custom license. See [LICENSE.md](LICENSE.md) for more details.

In general, if you're interested in creating something that falls outside the license terms, get in touch with Terry and we'll talk about it!

Authors
-------
- Created by [Terry Cavanagh](http://distractionware.com/)
- Room Names by [Bennett Foddy](http://www.foddy.net)
- Music by [Magnus Pålsson](http://souleye.madtracker.net/)
- Metal Soundtrack by [FamilyJules](http://familyjules7x.com/)
- 2.0 Update (C++ Port) by [Simon Roth](http://www.machinestudios.co.uk)
- 2.2 Update (SDL2/PhysicsFS/Steamworks port) by [Ethan Lee](http://www.flibitijibibo.com/)
- Beta Testing by Sam Kaplan and Pauli Kohberger
- Ending Picture by Pauli Kohberger

Versions
------------
There are two versions of the VVVVVV source code available - the [desktop version](https://github.com/TerryCavanagh/VVVVVV/tree/master/desktop_version) (based on the C++ port, and currently live on Steam), and the [mobile version](https://github.com/TerryCavanagh/VVVVVV/tree/master/mobile_version) (based on a fork of the original flash source code, and currently live on iOS and Android).


# mrb's notes

## Build instructions

I've only built on macOS 10.15 using Xcode 11.3. I installed third-party libs (like zlib and openssl) via brew.

1. Python 3.8 has to be installed into python3.8. I built it from source. On macOS 10.15, I had problems getting Python to find zlib and openssl. I had to do something like this:

        export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/usr/local/opt/zlib/lib/pkgconfig:/usr/local/opt/openssl@1.1/lib/pkgconfig"
        export LDFLAGS="-L/usr/local/opt/zlib/lib -L/usr/local/opt/openssl@1.1/lib"
        export CPPFLAGS="-I/usr/local/opt/zlib/include -I/usr/local/opt/openssl@1.1/include"
        make clean ; ./configure --prefix=/path/to/VVVVVV/python3.8 && make

    At the end of `make`, you'll get a list of modules that aren't being built. If you see _ssl or zlib on that list, you'll run into problems during `make install` or `pip` network operations.

2. Create a virtualenv:

        ./python3.8/bin/python3 -mvenv python3.8-venv
        ./python3.8-venv/bin/pip install -r desktop_version/src/swnhook/requirements.txt

3. Follow build instructions as normal. Copy data.zip from the commercial game into flibitBuild in order to run, and run it with `flibitBuild` as your working directory.

## Invocation notes

    cd desktop_version/flibitBuild
    ./vvvvvv.osx

* SWNHook.cpp has a relative path reference to `../src`, where it expects to find the `swnhook` python module (ie. `desktop_version/src/swnhook`). Assumption is that you're running it from `desktop_version/flibitBuild`, a directory that's a sibling to `src/`.
* `desktop_version/src/swnhook/__init__.py` contains a reference to `../../python3.8-venv/bin/activate_this.py` which is checked in to the repo. Assumption is that you're running from `desktop_version/flibitBuild` and put your Python venv into `<git_root>/python3.8-venv`.
