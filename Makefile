
all:

distclean:
	rm -rf build dist brobox.egg-info

wheel:
	python3 setup.py bdist_wheel

pypi-upload: distclean wheel
	twine upload --config-file .pypirc dist/brobox_client-*.whl
