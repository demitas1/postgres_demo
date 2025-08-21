FROM postgres:16

# Install dependencies, download and install pg_bigm, configure PostgreSQL, and clean up
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y --no-install-recommends \
  build-essential \
  curl \
  libicu-dev \
  postgresql-server-dev-16 \
  ca-certificates

# download and build pg_bigm
RUN cd /tmp \
  # Download and extract pg_bigm
  && curl -L -O https://github.com/pgbigm/pg_bigm/archive/refs/tags/v1.2-20240606.tar.gz \
  && tar zxf v1.2-20240606.tar.gz

# Build and install pg_bigm
RUN cd /tmp/pg_bigm-1.2-20240606 \
  && make USE_PGXS=1 \
  && make USE_PGXS=1 install

# Configure PostgreSQL to preload pg_bigm
RUN echo "shared_preload_libraries = 'pg_bigm'" >> /usr/share/postgresql/postgresql.conf.sample

# Cleanup
RUN cd / \
  && rm -rf /tmp/pg_bigm-1.2-20240606 \
  && apt-get remove -y build-essential \
  && apt-get autoremove -y \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Expose the PostgreSQL port  
EXPOSE 5432
