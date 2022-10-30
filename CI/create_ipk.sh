#!/bin/bash

# D=$(pushd $(dirname $0) &> /dev/null; pwd; popd &> /dev/null)
D=$(pwd) &> /dev/null
P=${D}/ipkg.tmp.$$
B=${D}/ipkg.build.$$

pushd ${D} &> /dev/null
VER=$(head -n 1 CHANGES.md | grep -i '## Version' | sed 's/^## Version \([[:digit:]]\+\.[[:digit:]]\+\.[[:digit:]]\+\)/\1/')
# '%cd': committer date (format respects --date= option); '%t': abbreviated tree hash
GITVER=git$(git log -1 --format="%cd" --date="format:%Y%m%d")-r$(git rev-list HEAD --since=yesterday --count)

PKG=${D}/enigma2-plugin-extensions-openwebif_${VER}-${GITVER}_all.ipk

popd &> /dev/null

mkdir -p ${P}
mkdir -p ${P}/CONTROL
mkdir -p ${B}

cat > ${P}/CONTROL/control << EOF
Package: enigma2-plugin-extensions-openwebif
Version: ${VER}-${GITVER}
Description: Control your receiver with a browser
Architecture: all
Section: extra
Priority: optional
Maintainer: E2OpenPlugins members
Homepage: https://github.com/oe-alliance/OpenWebif
Depends: python3-json, python3-cheetah, python3-pyopenssl, python3-unixadmin, python3-misc, python3-twisted-web, python3-pprint, python3-compression, python3-ipaddress
Source: https://github.com/oe-alliance/OpenWebif
EOF

mkdir -p ${P}/usr/lib/enigma2/python/Plugins/Extensions/OpenWebif/
cp -rp ${D}/plugin/* ${P}/usr/lib/enigma2/python/Plugins/Extensions/OpenWebif/
for f in $(find ./locale -name *.po ); do
	l=$(echo ${f%} | sed 's/\.po//' | sed 's/.*locale\///')
	mkdir -p ${P}/usr/lib/enigma2/python/Plugins/Extensions/OpenWebif/locale/${l%}/LC_MESSAGES
	msgfmt -o ${P}/usr/lib/enigma2/python/Plugins/Extensions/OpenWebif/locale/${l%}/LC_MESSAGES/OpenWebif.mo ./locale/$l.po
done

cheetah-compile -R ${P}/usr/lib/enigma2/python/Plugins/Extensions/OpenWebif/
python -O -m compileall ${P}/usr/lib/enigma2/python/Plugins/Extensions/OpenWebif/

tar -C ${P}/CONTROL -czf ${B}/control.tar.gz .
rm -rf ${P}/CONTROL
tar -C ${P} -czf ${B}/data.tar.gz .

echo "2.0" > ${B}/debian-binary

cd ${B}

ls -la
echo "Create ipk ${PKG}"
ar -r ${PKG} ./debian-binary ./data.tar.gz ./control.tar.gz 

rm -rf ${P}
rm -rf ${B}
