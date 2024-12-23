"""
Laravel Framework Implementation

Handles Laravel-specific Docker environment setup while maintaining the standard
Laravel installation and project structure conventions.
"""

from pathlib import Path
from typing import Dict, Any
import subprocess
from frameworks.php.base_php import BasePHPFramework

class LaravelFramework(BasePHPFramework):
    """Laravel framework implementation focusing on Docker environment setup."""

    def __init__(self, project_name: str, base_path: Path):
        super().__init__(project_name, base_path)
        self.docker_requirements.update({
            'php': {
                'image': 'php:8.2-fpm',
                'extensions': [
                    'pdo_mysql',
                    'mbstring',
                    'exif',
                    'pcntl',
                    'bcmath',
                    'gd'
                ]
            },
            'composer': {
                'image': 'composer:latest'
            }
        })

    def initialize_project(self) -> bool:
        """Initialize Laravel project using Docker."""
        try:
            subprocess.run([
                'docker', 'run', '--rm',
                '-v', f'{self.base_path}:/app',
                '-w', '/app',
                'composer:latest',
                'create-project',
                'laravel/laravel',
                self.project_name
            ], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error initializing Laravel project: {e}")
            return False

    def configure_docker(self) -> Dict[str, Any]:
        """Generate Laravel-specific Docker configuration."""
        config = {
            'services': {
                'php': {
                    'build': {
                        'context': '.',
                        'dockerfile': 'docker/php/Dockerfile'
                    },
                    'volumes': [
                        '.:/var/www/html:cached',
                        './docker/php/local.ini:/usr/local/etc/php/conf.d/local.ini:ro'
                    ],
                    'depends_on': ['mysql']
                },
                'nginx': {
                    'image': 'nginx:alpine',
                    'ports': [f"{self.get_default_ports()['web']}:80"],
                    'volumes': [
                        '.:/var/www/html:cached',
                        './docker/nginx/conf.d:/etc/nginx/conf.d:ro'
                    ],
                    'depends_on': ['php']
                },
                'mysql': {
                    'image': 'mysql:8.0',
                    'environment': {
                        'MYSQL_DATABASE': '${DB_DATABASE}',
                        'MYSQL_USER': '${DB_USERNAME}',
                        'MYSQL_PASSWORD': '${DB_PASSWORD}',
                        'MYSQL_ROOT_PASSWORD': '${DB_ROOT_PASSWORD}'
                    },
                    'ports': [f"{self.get_default_ports()['database']}:3306"],
                    'volumes': [
                        'mysql-data:/var/lib/mysql:cached'
                    ]
                },
                'redis': {
                    'image': 'redis:alpine',
                    'ports': [f"{self.get_default_ports()['redis']}:6379"]
                }
            },
            'volumes': {
                'mysql-data': None
            }
        }
        return config

    def get_default_ports(self) -> Dict[str, int]:
        """Return default ports for Laravel development."""
        return {
            'web': 8080,
            'database': 3306,
            'redis': 6379
        }

    def setup_development_environment(self) -> bool:
        """Set up Laravel development environment configurations."""
        try:
            self._create_docker_configs()
            return True
        except Exception as e:
            print(f"Error setting up Laravel environment: {e}")
            return False

    def _create_docker_configs(self) -> None:
        """Create necessary Docker configuration files."""
        docker_path = self.base_path / self.project_name / 'docker'
        docker_path.mkdir(exist_ok=True)

        self._create_php_dockerfile(docker_path / 'php')
        self._create_nginx_config(docker_path / 'nginx')

    def _create_php_dockerfile(self, path: Path) -> None:
        """Generate PHP Dockerfile with Laravel requirements."""
        path.mkdir(exist_ok=True)
        dockerfile_content = f"""
FROM {self.docker_requirements['php']['image']}

# Install dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    libpng-dev \\
    libonig-dev \\
    libxml2-dev \\
    zip \\
    unzip

# Install PHP extensions
RUN docker-php-ext-install \\
    {' '.join(self.docker_requirements['php']['extensions'])}

# Install Composer
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

WORKDIR /var/www/html
"""
        (path / 'Dockerfile').write_text(dockerfile_content.strip())

        # Create PHP configuration
        php_ini_content = """
upload_max_filesize=40M
post_max_size=40M
memory_limit=512M
"""
        (path / 'local.ini').write_text(php_ini_content.strip())

    def _create_nginx_config(self, path: Path) -> None:
        """Generate Nginx configuration for Laravel."""
        path.mkdir(exist_ok=True)
        nginx_config = """
server {
    listen 80;
    index index.php index.html;
    server_name localhost;
    root /var/www/html/public;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass php:9000;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
"""
        (path / 'conf.d').mkdir(exist_ok=True)
        (path / 'conf.d' / 'app.conf').write_text(nginx_config.strip())