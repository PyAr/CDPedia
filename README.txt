How to create an image
----------------------

All is automated nowadays, but you need to be sure that there is configuration
for the image type you want to produce.

For example, let's suppose you want to create a "dvd" version of Spanish
Wikipedia. Then, you need to be sure that there is configuration for 'es' in
the ``languages.yaml`` file, and for 'dvd' (in the 'es' section) in the
``imagtypes.yaml`` file.

Then all you have to do is get the project and run the CDPetron::

  utilities/cdpetron.py . /opt/somedir es

The first parameter is the project branch (usually just '.'), the second
directory is where all the dump from the web will go (be sure you have a
lot of free space!), and then the language.

In that example it will just produce *all image types*, for the example
we said before (just the normal DVD version), you can do::

  utilities/cdpetron.py . /opt/somedir es --image-type dvd5


Quick image
-----------

If you're just developing and want to do a quick test, you can run the
CDPetron with ``--test-mode``, which will not dump *everything* from the
web, just some pages.

Also, you have several parameters like ``--no-lists``, ``--no-scrap``,
and ``--no-clean`` which will help you to not do everything again on every
test cycle. Run the CDPetron with ``--help`` for info about those.
