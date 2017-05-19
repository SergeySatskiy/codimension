cd
sudo apt-get install python-virtualenv
sudo apt-get install libpcre3-dev
sudo apt-get install graphviz

virtualenv -p python3 p3
source p3/bin/activate

sudo apt-get install python3-dev

git clone https://github.com/SergeySatskiy/cdm-pythonparser.git
cd cdm-pythonparser
make
make check
python setup.py install --prefix ~/p3/

cd
git clone https://github.com/SergeySatskiy/cdm-flowparser.git
cd cdm-flowparser
make
make check
python setup.py install --prefix ~/p3/



cd
git clone https://github.com/andreikop/qutepart.git
cd qutepart
python setup.py install --prefix ~/p3/


cd
git clone https://github.com/SergeySatskiy/codimension.git
cd codimension
git checkout p3
cd src
ln -s ../thirdparty thirdparty


pip install PyQt5
pip install yapsy
pip install python-magic
pip install pyflakes

./codimension &
