FROM aida-test-base:latest

USER root

# Install PHP and Composer
RUN apt-get update && apt-get install -y \
    php8.3-cli \
    php8.3-mbstring \
    php8.3-xml \
    php8.3-curl \
    php8.3-zip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Composer
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

USER tester
WORKDIR /home/tester/projects/php-test-project

# Copy sample PHP project
COPY --chown=tester:tester sample-project/ .

# Install PHP dependencies
RUN composer install --no-interaction

# Initialize git repository
RUN git init \
    && git add . \
    && git commit -m "Initial commit: PHP test project"

CMD ["/bin/bash"]
