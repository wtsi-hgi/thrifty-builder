[![Build Status](https://travis-ci.org/wtsi-hgi/thrifty-builder.svg?branch=master)](https://travis-ci.org/wtsi-hgi/thrifty-builder)
[![codecov](https://codecov.io/gh/wtsi-hgi/thrifty-builder/branch/master/graph/badge.svg)](https://codecov.io/gh/wtsi-hgi/thrifty-builder)
[![PyPI version](https://badge.fury.io/py/thriftybuilder.svg)](https://badge.fury.io/py/thriftybuilder)

# Thrifty Builder
_Builds Docker images, capturing information to reduce the frequency of future re-builds_

## Introduction
Thrifty builder stores a hash of all the ingredients that go into building a Docker image so the tool is able to 
determine if an image has already been built before, even if the build cache has been emptied or if the build is taking
place on a different machine with a separate cache.

In our setup, we are building a large number of Docker images in our CI. The CI job runs on a different machine each 
time (with separate caches), meaning that if `docker build` was used, all images would be rebuild every time the CI 
runs. The aim is to minimise our CI run time and to keep our Docker images as stable as possible (it is usually 
extremely difficult to version everything that goes into an image so each re-build will create a slightly different 
image, even if the context and Dockerfile are the same).  


## Installation
Prerequisites
- Python 3.6+

The tool can be installed from PyPi:
```bash
pip install thriftybuilder
```

Bleeding edge versions can be installed directly from GitHub:
```bash
pip install git+https://github.com/wtsi-hgi/thrifty-builder.git@master#egg=thriftybuilder
```

## Usage
### Configuration
A build configuration YAML file is required to use the tool. This file details the images that are to be built, the 
Docker registries to push the created images to (optional) and the location of the checksum storage.

#### Storage
##### stdin/stdout
(Default if not specified) 
```yaml
checksum_storage:
  type: stdio
```

##### Local
```yaml
checksum_storage:
  type: local
  path: /root/.thrifty/checksums
``` 

##### Consul
```yaml
checksum_storage:
  type: consul
  url: https://example.com:8500           # Optional: derived from Consul environment variables if not set
  token: "{{ env[CONSUL_HTTP_TOKEN] }}"   # Optional: derived from Consul environment variables if not set
  key: ci/image-checksums
  lock: ci/image-checksums.lock
```
_Note: to use Consul-backed storage, the requirements in `consul_requirements.txt` must be installed (not done so by 
default)._


### CLI
```
usage: thrifty [-h] [-v] [--built-only] configuration-location

Builds Docker images, capturing information to reduce the frequency of future
re-builds (v1.0.0b0)

positional arguments:
  configuration-location
                        location of configuration

optional arguments:
  -h, --help            show this help message and exit
  -v                    increase the level of log verbosity (add multiple
                        increase further)
  --built-only          only print details about newly built images on stdout
```


### Example
_configuration.yml_
```yaml
docker:
  images:
    - name: wtsi-hgi/image-1
      dockerfile: /images/image-1/Dockerfile
      context: /images
    - name: wtsi-hgi/image-2
      dockerfile: /images/image-2/Dockerfile
      # Context assumed to be /images/image-2 
  registries:
    - url: https://docker.io
      username: "{{ env[DOCKER_IO_USERNAME] }}"
      password: "{{ env[DOCKER_IO_PASSWORD] }}"
      
checksum_storage:
  type: consul
  url: "{{ env[CONSUL_HTTP_ADDR] }}"
  token: "{{ env[CONSUL_HTTP_TOKEN] }}"
  key: ci/image-checksums
  lock: ci/image-checksums.lock
```

CLI:
```bash
thrifty configuration.yml
{"wtsi-hgi/image-1": "b2db4c1ae978201407c69573ba89a9b8", "wtsi-hgi/image-2": "f9a4d7cc9f7133756b36973cc2d888de"}

```


## Alternatives
- Share a build cache between all image building machines and make sure the cache is not lost.  
- More exotic Docker image builders might store information about the build context with the built image.
