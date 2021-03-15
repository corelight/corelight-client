
all:

distclean:
	rm -rf build dist corelight-client.egg-info

wheel:
	python3 setup.py bdist_wheel

pypi-upload: distclean wheel
	twine upload --config-file .pypirc dist/corelight_client-*.whl

pylint:
	pylint --rcfile=pylint.rc bin/corelight-client client
