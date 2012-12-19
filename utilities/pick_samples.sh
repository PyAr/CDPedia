#!/usr/bin/env bash

# get some samples from the articles directory

if [ $# -eq 2 ]; then
    ARTICLES=$1
    SAMPLES=$2
else
    echo "Usage: pick_samples.sh <wikipedia_dump_articles_dir> <samples_dir>"
    exit
fi

mkdir -p $SAMPLES/L/i/m
cp -pr $ARTICLES/L/i/m/*Limitac* $SAMPLES/L/i/m/

mkdir -p $SAMPLES/六/本
cp -pr $ARTICLES/六/本/木 $SAMPLES/六/本/

cp -pr $ARTICLES/Ñ $SAMPLES/

mkdir -p $SAMPLES/A/p
cp -pr $ARTICLES/A/p/o $SAMPLES/A/p/

mkdir -p $SAMPLES/A/c/e
cp -pr $ARTICLES/A/c/e/*Acerca* $SAMPLES/A/c/e/

mkdir -p $SAMPLES/A/m/é
cp -pr $ARTICLES/A/m/é/Portal:América* $SAMPLES/A/m/é/

mkdir -p $SAMPLES/A/v/i
cp -pr $ARTICLES/A/v/i/*Aviso* $SAMPLES/A/v/i/

mkdir -p $SAMPLES/A/s/t
cp -pr $ARTICLES/A/s/t/Portal:Astron* $SAMPLES/A/s/t/

mkdir -p $SAMPLES/D/e/r
cp -pr $ARTICLES/D/e/r/*Derechos* $SAMPLES/D/e/r/

mkdir -p $SAMPLES/T/u
cp -pr $ARTICLES/T/u/r $SAMPLES/T/u/

mkdir -p $SAMPLES/1/5
cp -pr $ARTICLES/1/5/4 $SAMPLES/1/5/

mkdir -p $SAMPLES/P/o/r
cp -pr $ARTICLES/P/o/r/*Port* $SAMPLES/P/o/r/
