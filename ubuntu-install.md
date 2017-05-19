# Running python 3 Codimension port on a fresh Ubuntu installation

## Install common packages
```shell
cd
sudo apt-get install python-virtualenv
sudo apt-get install libpcre3-dev
sudo apt-get install graphviz
sudo apt-get install python3-dev
```

## Create python 3 virtual environment
```shell
virtualenv -p python3 p3
source p3/bin/activate
```

## Install some python packages
```shell
pip install PyQt5
pip install yapsy
pip install python-magic
pip install pyflakes
```

## Install Codimension python parser
```shell
git clone https://github.com/SergeySatskiy/cdm-pythonparser.git
cd cdm-pythonparser
make
make check
python setup.py install --prefix ~/p3/
```

## Install Codimension control flow parser
```shell
cd
git clone https://github.com/SergeySatskiy/cdm-flowparser.git
cd cdm-flowparser
make
make check
python setup.py install --prefix ~/p3/
```

## Install an editor component
```shell
cd
git clone https://github.com/andreikop/qutepart.git
cd qutepart
python setup.py install --prefix ~/p3/
```

## Install Codimension
```shell
cd
git clone https://github.com/SergeySatskiy/codimension.git
cd codimension
git checkout p3
cd src
ln -s ../thirdparty thirdparty
```

## Run Codimension
```shell
./codimension &
```
