import charms.apt
import os
import requests
import shutil
from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import resource_get, status_set, log, open_port
from charmhelpers.core.host import service_start, service_stop, service_restart
from charmhelpers.fetch import apt_install
from charms.reactive import (
    set_state,
    when,
    hook,
    when_none,
    remove_state,
    only_once,
    when_file_changed,
)

config = hookenv.config()


def setup_plus(cert, key):
    status_set('maintenance', 'Installing NGINX Plus...')
    apt_install(['apt-transport-https', 'ca-certificates'])
    os.makedirs('/etc/ssl/nginx/', exist_ok=True)
    shutil.copy(cert, '/etc/ssl/nginx/')
    shutil.copy(key, '/etc/ssl/nginx/')
    conf_file = requests.get('https://cs.nginx.com/static/files/90nginx')
    with open("/etc/apt/apt.conf.d/90nginx", "wb") as conf:
        conf.write(conf_file.content)
    nginx_signing = requests.get('http://nginx.org/keys/nginx_signing.key')
    charms.apt.add_source('https://plus-pkgs.nginx.com/ubuntu nginx-plus', key=nginx_signing.text)


def setup_nginx():
    status_set('maintenance', 'Installing NGINX...')
    nginx_signing = requests.get('http://nginx.org/keys/nginx_signing.key')
    charms.apt.add_source('http://nginx.org/packages/ubuntu nginx', key=nginx_signing.text)


# handlers --------------------------------------------------------------------
@when_none('apt.installed.nginx-plus', 'apt.installed.nginx')
def install_nginx():
    """ Install nginx
    """
    status_set('maintenance', 'Installing NGINX')
    log('LOG: install NGINX')
    try:
        cert = resource_get('nginx-cert')
        key = resource_get('nginx-key')
        config_file = resource_get('config-file')
    except:
        cert = None
        key = None
        config_file = None

    if cert and key:
        setup_plus(cert, key)
        charms.apt.queue_install(['nginx-plus'])
        open_port('8080')
    else:
        setup_nginx()
        charms.apt.queue_install(['nginx'])

    if config_file:
        shutil.copy(config_file, '/etc/nginx/conf.d/')

    open_port('80')


@only_once()
@when('apt.installed.nginx-plus')
def set_nginx_plus():
    set_state('nginx.installed')
    status_set('active', 'NGINX Plus is ready')


@only_once()
@when('apt.installed.nginx')
def set_nginx():
    set_state('nginx.installed')
    status_set('active', 'NGINX is ready')


@when('nginx.installed')
def start_nginx():
    service_start('nginx')


@hook('upgrade-charm')
def remove_installed_state():
    remove_state('nginx.installed')
    remove_state('apt.installed.nginx-plus')
    remove_state('apt.installed.nginx')


@hook('stop')
def shutdown():
    service_stop('nginx')


@when_file_changed('/etc/nginx/default.conf')
def restart_service():
    service_restart('nginx')


# Example website.available reaction ------------------------------------------
"""
This example reaction for an application layer which consumes this nginx layer.
If left here then this reaction may overwrite your top-level reaction depending
on service names, ie., both nginx and ghost have the same reaction method,
however, nginx will execute since it's a higher precedence.

@when('nginx.available', 'website.available')
def configure_website(website):
    website.configure(port=config['port'])
"""
