FROM postgres:17
RUN apt-get update
RUN apt-get install -y postgresql-contrib
COPY init.sql /docker-entrypoint-initdb.d/
COPY pg_hba.conf /docker-entrypoint-initdb.d/
COPY setup.sh /docker-entrypoint-initdb.d/
EXPOSE 5432
CMD ["postgres"]
