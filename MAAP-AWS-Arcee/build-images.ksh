#!/usr/bin/env bash

cd main
docker build --tag 'main' .

cd ../ui 
docker build --tag 'ui' .

cd ../loader 
docker build --tag 'loader' .
