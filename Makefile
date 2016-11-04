USE_BRANDING := yes
IMPORT_BRANDING := yes
REPONAME := python-libs
DIRNAME := xcp
include $(B_BASE)/common.mk
include $(B_BASE)/rpmbuild.mk

PYTHON_LIB_VERSION := 2.0.0
PYTHON_LIB_RELEASE := $(shell $(shell $(call git_cset_number,$(REPONAME))); echo $$CSET_NUMBER)

REPO = $(call git_loc,python-libs)

PYTHON_LIB_SPEC := xcp-python-libs.spec
PYTHON_LIB_SRC_DIR := xcp-python-libs-$(PYTHON_LIB_VERSION)
PYTHON_LIB_SRC := $(RPM_SOURCESDIR)/xcp-python-libs-$(PYTHON_LIB_VERSION).tar.gz
PYTHON_LIB_SRPM := xcp-python-libs-$(PYTHON_LIB_VERSION)-$(PYTHON_LIB_RELEASE).src.rpm
PYTHON_LIB_STAMP := $(MY_OBJ_DIR)/.rpmbuild.python_lib.stamp

.PHONY: build
build: $(PYTHON_LIB_STAMP) $(MY_OUTPUT_DIR)/python-libs.inc
	cd tests && ./run-all-tests.sh

$(MY_OUTPUT_DIR)/python-libs.inc: $(MY_OUTPUT_DIR)/.dirstamp Makefile
	( echo PYTHON_LIBS_PKG_NAME := xcp-python-libs ;\
	  echo PYTHON_LIBS_PKG_VERSION := $(PYTHON_LIB_VERSION)-$(PYTHON_LIB_RELEASE) ;\
	  echo PYTHON_LIBS_PKG_FILE := RPMS/noarch/xcp-python-libs-$(PYTHON_LIB_VERSION)-$(PYTHON_LIB_RELEASE).noarch.rpm ;\
	) >$@

.PHONY: pylint
pylint:
	run-pylint.sh $(PYTHON_LIBS_SOURCES)

.PHONY: sources
sources: $(RPM_SRPMSDIR)/$(PYTHON_LIB_SRPM)

.PHONY: clean
clean:
	rm -f $(PYTHON_LIB_STAMP) $(PYTHON_LIB_SRC) $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC)

.SECONDARY: $(PYTHON_LIB_SRC)
$(PYTHON_LIB_SRC): $(RPM_SOURCESDIR)/.dirstamp
	cd $(REPO) && git archive --format=tar --prefix=$(PYTHON_LIB_SRC_DIR)/ HEAD >$(@:%.gz=%)
	mkdir -p $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)/$(DIRNAME)
	{ $(call brand-python); \
	  echo "try:"; \
	  echo "    from oem_version import *"; \
	  echo "except:"; \
	  echo "    pass"; \
	} > $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)/$(DIRNAME)/branding.py
	tar rvf $(@:%.gz=%) -C $(MY_OBJ_DIR) $(PYTHON_LIB_SRC_DIR)/$(DIRNAME)/branding.py
	gzip $(@:%.gz=%)

.SECONDARY: $(xPYTHON_LIB_SRC)
$(xPYTHON_LIB_SRC): $(PYTHON_LIBS_SOURCES)
	$(call mkdir_clean,$(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR))
	mkdir -p $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)/$(DIRNAME)
	$(FIND_CMD) | cpio -pduv $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)/$(DIRNAME)
	{ $(call brand-python); \
	  echo "try:"; \
	  echo "    from oem_version import *"; \
	  echo "except:"; \
	  echo "    pass"; \
	} > $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)/$(DIRNAME)/branding.py
	mv -f $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)/$(DIRNAME)/setup.py $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)
	tar zcf $@ -C $(MY_OBJ_DIR) $(PYTHON_LIB_SRC_DIR)
	rm -rf $(MY_OBJ_DIR)/$(PYTHON_LIB_SRC_DIR)

.SECONDARY: $(RPM_SPECSDIR)/%.spec
$(RPM_SPECSDIR)/%.spec: *.spec.in Makefile
	sed -e 's/@PYTHON_LIB_VERSION@/$(PYTHON_LIB_VERSION)/g' \
	  -e 's/@PYTHON_LIB_RELEASE@/$(PYTHON_LIB_RELEASE)/g' \
	  < $< \
	  > $@

$(RPM_SRPMSDIR)/$(PYTHON_LIB_SRPM): $(RPM_DIRECTORIES) $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC) $(PYTHON_LIB_SRC)
	$(RPMBUILD) -bs $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC)

$(PYTHON_LIB_STAMP): $(RPM_SRPMSDIR)/$(PYTHON_LIB_SRPM)
	# work around rpmbuild removing source and spec
	ln -f $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC) $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC).keep
	ln -f $(PYTHON_LIB_SRC) $(PYTHON_LIB_SRC).keep
	$(RPMBUILD) --define "dirname $(DIRNAME)" --rebuild $(RPM_SRPMSDIR)/$(PYTHON_LIB_SRPM)
	mv -f $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC).keep $(RPM_SPECSDIR)/$(PYTHON_LIB_SPEC)
	mv -f $(PYTHON_LIB_SRC).keep $(PYTHON_LIB_SRC)
	touch $@
