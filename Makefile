USE_BRANDING := yes
IMPORT_BRANDING := yes
REPONAME := python-libs
DIRNAME := xcp
include $(B_BASE)/common.mk
include $(B_BASE)/rpmbuild.mk

-include $(MY_OBJ_DIR)/version.inc
.PHONY: $(MY_OBJ_DIR)/version.inc
$(MY_OBJ_DIR)/version.inc:
	$(version-makefile) > $@
	$(call hg_cset_number,$(REPONAME)) >> $@
	echo PYTHON_LIB_VERSION := \$$\(PRODUCT_VERSION\) >> $@
	echo PYTHON_LIB_RELEASE := xs\$$\(CSET_NUMBER\) >> $@

PYTHON_LIBS_SOURCES := $(wildcard *.py)

PYTHON_LIB_SPEC := python-libs.spec
PYTHON_LIB_SRC_DIR := python-libs-$(PYTHON_LIB_VERSION)
PYTHON_LIB_SRC := $(RPM_SOURCESDIR)/python-libs-$(PYTHON_LIB_VERSION).tar.gz
PYTHON_LIB_SRPM := python-libs-$(PYTHON_LIB_VERSION)-$(PYTHON_LIB_RELEASE).src.rpm
PYTHON_LIB_STAMP := $(MY_OBJ_DIR)/.rpmbuild.python_lib.stamp

.PHONY: build
build: $(PYTHON_LIB_STAMP)

$(MY_SOURCES)/MANIFEST: $(MY_SOURCES_DIRSTAMP) $(RPM_BUILD_COOKIE)
	( echo "$(COMPONENT) gpl file $(RPM_SRPMSDIR)/$(PYTHON_LIB_SRPM)" ; \
	) >$@

.PHONY: sources
sources: $(MY_SOURCES)/MANIFEST

.PHONY: clean
clean:
	rm -f $(PYTHON_LIB_STAMP) $(PYTHON_LIB_SRC) $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC)

.SECONDARY: $(PYTHON_LIB_SRC)
$(PYTHON_LIB_SRC): $(PYTHON_LIBS_SOURCES)
	$(call mkdir_clean,$(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR))
	mkdir -p $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)/$(DIRNAME)
	cp -f $^ $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)/$(DIRNAME)
	mv -f $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)/$(DIRNAME)/setup.py $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)
	tar zcf $@ -C $(MY_OBJ_DIR) $(PYTHON_LIB_SRC_DIR)
	rm -rf $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)

.SECONDARY: $(RPM_SPECSDIR)/%.spec
$(RPM_SPECSDIR)/%.spec: *.spec
	cp -f $^ $@

$(RPM_SRPMSDIR)/$(PYTHON_LIB_SRPM): $(RPM_DIRECTORIES) $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC) $(PYTHON_LIB_SRC)
	$(RPMBUILD) --define "version $(PYTHON_LIB_VERSION)" --define "release $(PYTHON_LIB_RELEASE)" -bs $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC)

$(PYTHON_LIB_STAMP): $(RPM_SRPMSDIR)/$(PYTHON_LIB_SRPM)
	# work around rpmbuild removing source and spec
	ln -f $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC) $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC).keep
	ln -f $(PYTHON_LIB_SRC) $(PYTHON_LIB_SRC).keep
	$(RPMBUILD) --define "dirname $(DIRNAME)" --rebuild $(RPM_SRPMSDIR)/$(PYTHON_LIB_SRPM)
	mv -f $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC).keep $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC)
	mv -f $(PYTHON_LIB_SRC).keep $(PYTHON_LIB_SRC)
	touch $@
