[![Build Status](https://travis-ci.org/wtsi-hgi/thrifty-builder.svg?branch=master)](https://travis-ci.org/wtsi-hgi/thrifty-builder)
[![codecov](https://codecov.io/gh/wtsi-hgi/thrifty-builder/branch/master/graph/badge.svg)](https://codecov.io/gh/wtsi-hgi/thrifty-builder)

# Thrifty Builder
Example configuration:
```yaml
docker_images:
  - name: wtsi-hgi/image-1
    dockerfile: /images/image-1/Dockerfile
    context: /images
  - name: wtsi-hgi/image-2
    dockerfile: /images/image-2/Dockerfile
    # Context assumed to be /images/image-2 
```