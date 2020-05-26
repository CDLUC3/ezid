TESTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
pushd ${TESTDIR}/test_docs
for f in $(ls *.bdb); do
  A=${f%_*};
  B={f##*_};
  C=${B%.*};
  D=${HOME}/.minders/${A}/${C};
  mkdir -p ${D};
  cp ${f} ${D}/nog.bdb;
done
popd
