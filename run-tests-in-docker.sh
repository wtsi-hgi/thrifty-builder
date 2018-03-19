#!/usr/bin/env bash

set -euf -o pipefail

scriptDirectory="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Note: `mktemp` creates temps in directory that cannot be mounted by default on Mac
tempDirectory="/tmp/thrifty-builder-${RANDOM}"
trap "echo ${tempDirectory} && rm -rf ${tempDirectory}" INT TERM HUP EXIT
mkdir "${tempDirectory}"

docker build -t thrifty-builder-tests -f Dockerfile.test .
docker run --rm -it -v "${scriptDirectory}":/thrifty \
                    -v /var/run/docker.sock:/var/run/docker.sock:ro \
                    -v "${tempDirectory}:${tempDirectory}" \
                    -e TMPDIR="${tempDirectory}" \
                    thrifty-builder-tests
