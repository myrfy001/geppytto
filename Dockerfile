FROM ubuntu:18.04

ADD sources.list /etc/apt/

# ensure local python is preferred over distribution python
ENV PATH /usr/local/bin:$PATH

# http://bugs.python.org/issue19846
# > At the moment, setting "LANG=C" on a Linux system *fundamentally breaks Python 3*, and that's not OK.
ENV LANG C.UTF-8

ENV DEBIAN_FRONTEND noninteractive
# extra dependencies (over what buildpack-deps already includes)
RUN apt-get update && apt-get build-dep python3.6  -y --no-install-recommends && \

    # Following for Chrome
    echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections && \
    apt-get install -y software-properties-common && \
    apt-add-repository ppa:malteworld/ppa && \
    apt-get install -y --no-install-recommends \
      msttcorefonts \
      fonts-noto-color-emoji \
      fonts-noto-cjk \
      fonts-liberation \
      fonts-thai-tlwg \
      fontconfig \
      libappindicator3-1 \
      pdftk \
      unzip \
      locales \
      gconf-service \
      libasound2 \
      libatk1.0-0 \
      libc6 \
      libcairo2 \
      libcups2 \
      libdbus-1-3 \
      libexpat1 \
      libfontconfig1 \
      libgcc1 \
      libgconf-2-4 \
      libgdk-pixbuf2.0-0 \
      libglib2.0-0 \
      libgtk-3-0 \
      libnspr4 \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libstdc++6 \
      libx11-6 \
      libx11-xcb1 \
      libxcb1 \
      libxcomposite1 \
      libxcursor1 \
      libxdamage1 \
      libxext6 \
      libxfixes3 \
      libxi6 \
      libxrandr2 \
      libxrender1 \
      libxss1 \
      libxtst6 \
      ca-certificates \
      libappindicator1 \
      libnss3 \
      lsb-release \
      xdg-utils \
      wget \
      xvfb \
      curl && \
    # Fonts
    fc-cache -f -v && \

	  rm -rf /var/lib/apt/lists/*


ENV GPG_KEY 0D96DF4D4110E5C43FBFB17F2D347EA6AA65421D
ENV PYTHON_VERSION 3.6.7

RUN set -ex \
	\
	&& wget -O python.tar.xz "https://www.python.org/ftp/python/${PYTHON_VERSION%%[a-z]*}/Python-$PYTHON_VERSION.tar.xz" \
	# && wget -O python.tar.xz.asc "https://www.python.org/ftp/python/${PYTHON_VERSION%%[a-z]*}/Python-$PYTHON_VERSION.tar.xz.asc" \
	# && export GNUPGHOME="$(mktemp -d)" \
	# && gpg --batch --keyserver ha.pool.sks-keyservers.net --recv-keys "$GPG_KEY" \
	# && gpg --batch --verify python.tar.xz.asc python.tar.xz \
	# && { command -v gpgconf > /dev/null && gpgconf --kill all || :; } \
	# && rm -rf "$GNUPGHOME" python.tar.xz.asc \
	&& mkdir -p /usr/src/python \
	&& tar -xJC /usr/src/python --strip-components=1 -f python.tar.xz \
	&& rm python.tar.xz \
	\
	&& cd /usr/src/python \
	&& gnuArch="$(dpkg-architecture --query DEB_BUILD_GNU_TYPE)" \
	&& ./configure \
		--build="$gnuArch" \
		--enable-loadable-sqlite-extensions \
		--enable-shared \
		--with-system-expat \
		--with-system-ffi \
		--without-ensurepip \
	&& make -j "$(nproc)" \
	&& make install \
	&& ldconfig \
	\
	&& find /usr/local -depth \
		\( \
			\( -type d -a \( -name test -o -name tests \) \) \
			-o \
			\( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \
		\) -exec rm -rf '{}' + \
	&& rm -rf /usr/src/python \
	\
	&& python3 --version

# make some useful symlinks that are expected to exist
RUN cd /usr/local/bin \
	&& ln -s idle3 idle \
	&& ln -s pydoc3 pydoc \
	&& ln -s python3 python \
	&& ln -s python3-config python-config

# if this is called "PIP_VERSION", pip explodes with "ValueError: invalid truth value '<VERSION>'"
ENV PYTHON_PIP_VERSION 18.1

RUN set -ex; \
	\
	wget -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'; \
	\
	python get-pip.py \
		--disable-pip-version-check \
		--no-cache-dir \
		"pip==$PYTHON_PIP_VERSION" \
	; \
	pip --version; \
	\
	find /usr/local -depth \
		\( \
			\( -type d -a \( -name test -o -name tests \) \) \
			-o \
			\( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \
		\) -exec rm -rf '{}' +; \
	rm -f get-pip.py





# Application parameters and variables
ENV HOST=0.0.0.0
ENV PORT=3000
ENV application_directory=/usr/src/app
ENV ENABLE_XVBF=true


# Configuration for Chrome
ENV CONNECTION_TIMEOUT=60000
ENV CHROME_PATH=/usr/bin/google-chrome

RUN mkdir -p $application_directory

WORKDIR $application_directory


RUN apt-get update && apt-get install -y gdb


# Add user
RUN groupadd -r geppytto && useradd -r -g geppytto -G audio,video geppytto \
  && mkdir -p /home/geppytto/Downloads \
  && chown -R geppytto:geppytto /home/geppytto \
  && chown -R geppytto:geppytto $application_directory

RUN cd /tmp && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    dpkg -i google-chrome-stable_current_amd64.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# It's a good idea to use dumb-init to help prevent zombie chrome processes.
ADD https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_amd64 /usr/local/bin/dumb-init
RUN chmod +x /usr/local/bin/dumb-init


# Install app dependencies
COPY requirements.txt .
RUN pip install --no-cache -r requirements.txt

# Bundle app source
COPY . .


# Run everything after as non-privileged user.
USER geppytto

# Expose the web-socket and HTTP ports
EXPOSE 9990
ENTRYPOINT ["dumb-init", "--"]
ENV GEPPYTTO_CHROME_EXECUTABLE_PATH=/opt/google/chrome/chrome
