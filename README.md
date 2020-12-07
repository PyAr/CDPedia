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

Alternatively, just use [fades](https://github.com/PyAr/fades/) to deal with the virtualenv automatically:

    fades -r requirements-dev.txt cdpetron.py /opt/somedir es

The first parameter is where all the dump from the web will go (pages, images, etc... be sure you have a lot of free space!), and then the language.

In those examples CDPetron will produce *all the image types*. To specify a particular iamge type to be built, you can use the `--image-type` option (remember that it needs to be defined in the `imagtypes.yaml` file):

    ./cdpetron.py /opt/somedir es --image-type dvd5

If the process is interrupted (a full CDPedia generation may take *days*), don't despair! The generation process checks for what is already done to avoid doing it again; so even it doesn't exactly resumes from where was interrupted, a lot of time is saved in the subsequent runs. That said, you may want to use `--no-lists` and `--no-scrap` options, to avoid getting fresh info to work on.


## Dependencies

The following programs are used by the building process (needs to be previously installed):

    pngquant
    pip

Some helpers (like `run` or `test`) use [fades]( https://github.com/PyAr/fades/) to deal with virtualenvs automatically, it's a good idea to also have it installed.

No further dependencies are needed by the *final running CDPedia*, the creation process already manages its Python dependencies.


## Quick image creation

If you're just developing and want to do a quick test, you can run the CDPetron with the `--test-mode` option, and it will not dump *everything* from the web, just some pages.

    ./cdpetron.py /opt/somedir es --test-mode

Also, you have several parameters like ``--no-lists``, ``--no-scrap``, and ``--no-clean`` which will help you to not do everything again on every test cycle. Run the CDPetron with ``--help`` for info about those.


## Creating an image with specific pages

The `cdpetron` sctip has some specific option to help testing some specific pages when developing.

These are not to be confused with `--test-mode`, which builds a small functional CDPedia, but with first 1000 pages, not the ones you want to check. That said, the best way to use these are together with `--test-mode`, which makes everything faster.

First one is `--extra-pages`, which allows you to specify a file with a list of pages to be downloaded. 

Second one is `--page-limit`, to limit the quantity of pages to download/scrap.

For example, then:

    ./cdpetron.py /opt/somedir es --test-mode --extra-pages=/tmp/extra.txt --page-limit=50


# How to add a new lenguage

CDpedia is multilenguage, so you can generate it in Spanish, Portuguese, German, or whatever, with the only condition than the there is a Wikipedia online for that language

Currently in the project everything is setup for the following languages:

- Aymara (`ay`)
- French (`fr`)
- Portuguese (`pt`)
- Spanish (`es`)

You can add the proper structures for another language of your preference, and generate the CDPedia for that language. We encourage you to submit a PR with those structures for the new language so they are available for everybody else, thanks!

So, to add a new lenguage you need to take care of different things: language configuration (`imagtypes.yaml` and `languages.yaml`), service texts for the running CDPedia, and project web page for the public. 

Let's see these in detail (you can see current files for real life examples):

- `imagtypes.yaml`: here you need to create a new entry for the language you're creating, and the different CDPedia images that you could produce in that language. For each image kind:

    - `type`: the type of file that will hold the CDPedia: `tarball` to create a `.tar.xz` file, aimed to be distributed in pendrives or similar, or `iso`, aimed to be burned into CDs or DVDs.

    - `windows`: True or False, indicating if Windows support needs to be included in CDPedia.

    - `page_limit`: how many Wikipedia pages will be included in CDPedia (these will be the top N most important pages from Wikipedia for the language); note that this is the main factor that impacts in the final size of the CDPedia image.

    - `image_reduction`: four values (M, N, P, and Q, adding 100) that determine how the images included in the pages will be treated; after selecting the best pages to include in the CDPedia, the process will grab the images for those pages, and M% of the total of those images will be included at 100% size, N% will be included at 75% size, P% will be included at 50% size, and Q% will NOT be included; note this also impacts heavily in the final size of the CDPedia result.

- `languages.yaml`: again create the entry for your language, with the following config:

    - `portal_index`: the Wikipedia page that will be the first page shown when CDPedia is started.

    - `include`: the list of Wikipedia pages that are mandatory for that language (normally these are pointed to from the main template itself, common to all the "content pages" shown.

    - `python_docs`: the URL of the tarball of Python documentation in HTML format desired for the language.

    - `second_language`: the two-letters code for the default language that will be used when translating all texts; so if a particular text is not translated to your new language, the correspondent text from this "second language" will be used (if not specified, the second language will be English).
    
- generate the translations for all texts that are used in the templates of the running service; these are all the words and sentences that people will find when running the distributed CDPedia file. For this, just follow the instructions in [this HowTo](locale/HOWTO.txt).

- translate the web page that is used to [show the project for the general public](http://cdpedia.python.org.ar/): in this case you need to just copy the [English template](web/templates/index_template.en.html) as another file in the same directory, and translate all the texts in that template.
