check_package() {
    PKG_OK=$(dpkg-query -W --showformat='${Status}\n' $1|grep "install ok installed")
    echo Checking for $1: $PKG_OK
    if [ "" = "$PKG_OK" ]; then 
        echo "No $1. Setting up $1."
        sudo apt-get --yes install $1 
    else
        exit 1
    fi
    }


test_ok () {
    status=$?
    if test $status -ne 0; then 
        echo Error status $status
        exit 1 
    fi 
}

cwd=$(pwd)
mkdir tutorialpython
cd tutorialpython
echo "Cloning python-docs repository"
git clone https://github.com/python/python-docs-es.git
test_ok

cd python-docs-es
echo "Creating virtual environment"
# check_package python3-venv
python3 -m venv venv
test_ok
source venv/bin/activate
test_ok

echo "Making setup"
make setup
test_ok

echo "Compiling html documentation"
make build
test_ok

tutpath="cpython/Doc/_build/html/tutorial" 
if [ -d "$tutpath" ]; then
    echo "Copy to destination folder"
    cp -r $tutpath/*.html $cwd
    cd $cwd
    echo "Delete working directory"
    rm -rf tutorialpython/python-doc-es
fi
