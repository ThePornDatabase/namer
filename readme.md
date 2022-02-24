[![workflow](https://github.com/4c0d3r/namer/actions/workflows/ci.yml/badge.svg)](https://github.com/4c0d3r/namer/actions/workflows/ci.yml/)
[![codecov](https://codecov.io/gh/4c0d3r/namer/branch/main/graph/badge.svg?token=4MQEN2NUKZ)](https://codecov.io/gh/4c0d3r/namer)
### Namer

Given a file of the form ```<watchdir_location>/site-yy.mm.dd-name.parts.XXX.2160p/abc.mp4```, extracts info from the file name and looks up relevant metatdata.


That metadata is used to rename the dir and file, and push the new dir to ```<successful_dir_location>/Site - yyyy-MM-dd - scene name/Site - yyyy-MM-dd - scene name.mp4```.


The mp4's metadata is also set in a way that can be read by Apple TV app, quicktime, etc.   Default audio streams can also be cleaned up for quicktime, by setting a language prefernce in ```namer.cfg```


build docker file with ./docker_build.sh (no input).


running the docker file, here's a docker compose file which can serve as an example:


```docker-compose

---
version: "3"
services:  
  namer:
    container_name: namer
    image: porndb/namer:latest
    environment:
      - PUID=1001
      - PGID=1000
      - TZ=America/Los_Angeles
      - NAMER_CONFIG=/config/namer.cfg
    volumes:
      - /apps/namer/:/config
      - /media:/data
    devices:
      - /dev/dri/:/dev/dri/
    privileged: true
    restart: always

```

copy namer.cfg to a path mapped to /config/namer.cfg, and set values for your setup.   The config is well commented.


