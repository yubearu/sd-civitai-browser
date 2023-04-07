# installer script for some PyPI packages we need...

import launch
pkgs = [
        {"fake_useragent": "fake-useragent"},
        {"PIL": "PIL"},
        {"requests": "requests"}
       ]

for pkg in pkgs:
    key, val = next(iter(pkg.items()))
    if not launch.is_installed(key):
        print(f'installing "{val}"')
        launch.run_pip(f'install {val}', "requirements for CivitAI Browser")
