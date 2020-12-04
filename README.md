# CDPedia

CDPedia is a project to make the Wikipedia accesable offline.

Check also the [official page for normal humans](http://cdpedia.python.org.ar/).


## How to create an image

All is automated nowadays, but you need to be sure that there is configuration for the image type you want to produce.

For example, let's suppose you want to create a DVD version of Spanish Wikipedia. Then, you need to be sure that there is configuration for `es` in the `languages.yaml` file, and for `dvd` (in the `es` section) in the `imagtypes.yaml` file.

The next step is to run the CDPetron (for which you need to first create an activate a virtualenv):

    virtualenv --python=python3 venv
    source venv/bin/activate
    pip install -r requirements-dev.txt  

Then run the CDPetron itself:

    ./cdpetron.py /opt/somedir es

Alternatively, just use [fades]( https://github.com/PyAr/fades/) to deal with the virtualenv automatically:

    fades -r requirements-dev.txt cdpetron.py /opt/somedir es

The first parameter is where all the dump from the web will go (pages, images, etc... be sure you have a lot of free space!), and then the language.

In those examples CDPetron will produce *all the image types*. To specify a particular iamge type to be built, you can use the `--image-type` option (remember that it needs to be defined in the `imagtypes.yaml` file):

  ./cdpetron.py /opt/somedir es --image-type dvd5


# Dependencies

The following programs are used by the building process (needs to be previously installed):

    pngquant
    pip

Some helpers (like `run` or `test`) use [fades]( https://github.com/PyAr/fades/) to deal with virtualenvs automatically, it's a good idea to also have it installed.

No further dependencies are needed by the *final running CDPedia*, the creation process already manages its Python dependencies.


## Quick image creation

If you're just developing and want to do a quick test, you can run the CDPetron with the `--test-mode` option, and it will not dump *everything* from the web, just some pages.

  ./cdpetron.py /opt/somedir es --test-mode

Also, you have several parameters like ``--no-lists``, ``--no-scrap``, and ``--no-clean`` which will help you to not do everything again on every test cycle. Run the CDPetron with ``--help`` for info about those.


## How to add a new lenguage

CDpedia is multilenguage, so you can generate it in Spanish, Portuguese, German, or whatever, with the only condition than the there is a Wikipedia online for that language

Currently in the project everything is setup for the following languages:

- Aymara (`ay`)
- French (`fr`)
- Portuguese (`pt`)
- Spanish (`es`)

You can add the proper structures for another language of your preference, and generate the CDPedia for that language. We encourage you to submit a PR with those structures for the new language so they are available for everybody else, thanks!

So, to add a new lenguage you need to do the following steps:

    FIXME
