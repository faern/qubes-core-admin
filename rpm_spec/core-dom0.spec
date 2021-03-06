#
# This is the SPEC file for creating binary RPMs for the Dom0.
#
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2010  Joanna Rutkowska <joanna@invisiblethingslab.com>
# Copyright (C) 2010  Rafal Wojtczuk  <rafal@invisiblethingslab.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#

%{!?python_sitearch: %define python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)")}

%{!?version: %define version %(cat version)}

# debug_package hack should be removed when BuildArch:noarch is enabled below
%define debug_package %{nil}

%define _dracutmoddir	/usr/lib/dracut/modules.d
%if %{fedora} < 17
%define _dracutmoddir   /usr/share/dracut/modules.d
%endif

Name:		qubes-core-dom0
Version:	%{version}
Release:	1%{dist}
Summary:	The Qubes core files (Dom0-side)

Group:		Qubes
Vendor:		Invisible Things Lab
License:	GPL
URL:		http://www.qubes-os.org
BuildRequires:  ImageMagick
BuildRequires:	systemd-units
# FIXME: Enable this and disable debug_package
#BuildArch: noarch
Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units
Requires:	python, pciutils, python-inotify, python-daemon
Requires:       qubes-core-dom0-linux >= 3.1.8
Requires:       qubes-db-dom0
Requires:       python-lxml
Requires:       python-psutil
# TODO: R: qubes-gui-dom0 >= 2.1.11
Conflicts:      qubes-gui-dom0 < 1.1.13
Requires:       libvirt-python
%if x%{?backend_vmm} == xxen
Requires:       xen-runtime
Requires:       xen-hvm
Requires:       libvirt-daemon-xen >= 1.2.20-4
%endif
Requires:       createrepo
Requires:       gnome-packagekit
Requires:       cronie
Requires:       bsdtar
# for qubes-hcl-report
Requires:       dmidecode
Requires:       PyQt4

# Prevent preupgrade from installation (it pretend to provide distribution upgrade)
Obsoletes:	preupgrade < 2.0
Provides:	preupgrade = 2.0
%define _builddir %(pwd)

%description
The Qubes core files for installation on Dom0.

%prep
# we operate on the current directory, so no need to unpack anything
# symlink is to generate useful debuginfo packages
rm -f %{name}-%{version}
ln -sf . %{name}-%{version}
%setup -T -D

%build

make all

%install

make install \
    DESTDIR=$RPM_BUILD_ROOT \
    UNITDIR=%{_unitdir} \
    PYTHON_SITEPATH=%{python_sitearch} \
    SYSCONFDIR=%{_sysconfdir}

%post

# Create NetworkManager configuration if we do not have it
if ! [ -e /etc/NetworkManager/NetworkManager.conf ]; then
echo '[main]' > /etc/NetworkManager/NetworkManager.conf
echo 'plugins = keyfile' >> /etc/NetworkManager/NetworkManager.conf
echo '[keyfile]' >> /etc/NetworkManager/NetworkManager.conf
fi

sed '/^autoballoon=/d;/^lockfile=/d' -i /etc/xen/xl.conf
echo 'autoballoon=0' >> /etc/xen/xl.conf
echo 'lockfile="/var/run/qubes/xl-lock"' >> /etc/xen/xl.conf

sed 's/^PRELINKING\s*=.*/PRELINKING=no/' -i /etc/sysconfig/prelink

systemctl --no-reload enable qubes-core.service >/dev/null 2>&1
systemctl --no-reload enable qubes-netvm.service >/dev/null 2>&1
systemctl --no-reload enable qubes-setupdvm.service >/dev/null 2>&1

# Conflicts with libxl stack, so disable it
systemctl --no-reload disable xend.service >/dev/null 2>&1
systemctl --no-reload disable xendomains.service >/dev/null 2>&1
systemctl daemon-reload >/dev/null 2>&1 || :

HAD_SYSCONFIG_NETWORK=yes
if ! [ -e /etc/sysconfig/network ]; then
    HAD_SYSCONFIG_NETWORK=no
    # supplant empty one so NetworkManager init script does not complain
    touch /etc/sysconfig/network
fi

# Load evtchn module - xenstored needs it
modprobe evtchn 2> /dev/null || modprobe xen-evtchn
service xenstored start

if ! [ -e /var/lib/qubes/qubes.xml ]; then
#    echo "Initializing Qubes DB..."
    umask 007; sg qubes -c qvm-init-storage
    qubes-prefs -s default-kernel `ls /var/lib/qubes/vm-kernels|head -n 1` 2> /dev/null
fi

# Because we now have an installer
# this script is always executed during upgrade
# and we decided not to restart core during upgrade
#service qubes_core start

if [ "x"$HAD_SYSCONFIG_NETWORK = "xno" ]; then
    rm -f /etc/sysconfig/network
fi

%clean
rm -rf $RPM_BUILD_ROOT
rm -f %{name}-%{version}

%pre
if ! grep -q ^qubes: /etc/group ; then
		groupadd qubes
fi

%triggerin -- xen-runtime
/usr/lib/qubes/fix-dir-perms.sh

%preun
if [ "$1" = 0 ] ; then
	# no more packages left
    service qubes_netvm stop
    service qubes_core stop
fi

%postun
if [ "$1" = 0 ] ; then
	# no more packages left
    chgrp root /etc/xen
    chmod 700 /etc/xen
    groupdel qubes
fi

%files
%defattr(-,root,root,-)
%config(noreplace) %attr(0664,root,qubes) %{_sysconfdir}/qubes/qmemman.conf
%config(noreplace) %attr(0664,root,qubes) %{_sysconfdir}/qubes/storage.conf
/usr/bin/qvm-*
/usr/bin/qubes-*
%dir %{python_sitearch}/qubes
%{python_sitearch}/qubes/qubes.py
%{python_sitearch}/qubes/qubes.pyc
%{python_sitearch}/qubes/qubes.pyo
%{python_sitearch}/qubes/qubesutils.py
%{python_sitearch}/qubes/qubesutils.pyc
%{python_sitearch}/qubes/qubesutils.pyo
%{python_sitearch}/qubes/guihelpers.py
%{python_sitearch}/qubes/guihelpers.pyc
%{python_sitearch}/qubes/guihelpers.pyo
%{python_sitearch}/qubes/notify.py
%{python_sitearch}/qubes/notify.pyc
%{python_sitearch}/qubes/notify.pyo
%{python_sitearch}/qubes/backup.py
%{python_sitearch}/qubes/backup.pyc
%{python_sitearch}/qubes/backup.pyo
%{python_sitearch}/qubes/storage/*.py
%{python_sitearch}/qubes/storage/*.pyc
%{python_sitearch}/qubes/storage/*.pyo
%{python_sitearch}/qubes/settings.py
%{python_sitearch}/qubes/settings.pyc
%{python_sitearch}/qubes/settings.pyo
%{python_sitearch}/qubes/qmemman*.py*
%{python_sitearch}/qubes/modules/0*.py*
%{python_sitearch}/qubes/modules/__init__.py*
%{python_sitearch}/qubes/tests
/usr/lib/qubes/unbind-pci-device.sh
/usr/lib/qubes/cleanup-dispvms
/usr/lib/qubes/qmemman_daemon.py*
/usr/lib/qubes/qfile-daemon-dvm*
/usr/lib/qubes/block-cleaner-daemon.py*
/usr/lib/qubes/vusb-ctl.py*
/usr/lib/qubes/xl-qvm-usb-attach.py*
/usr/lib/qubes/xl-qvm-usb-detach.py*
/usr/lib/qubes/fix-dir-perms.sh
/usr/lib/qubes/startup-dvm.sh
/usr/lib/qubes/startup-misc.sh
/usr/lib/qubes/prepare-volatile-img.sh
/usr/libexec/qubes/qubes-notify-tools
/usr/libexec/qubes/qubes-notify-updates
%{_unitdir}/qubes-block-cleaner.service
%{_unitdir}/qubes-core.service
%{_unitdir}/qubes-setupdvm.service
%{_unitdir}/qubes-netvm.service
%{_unitdir}/qubes-qmemman.service
%{_unitdir}/qubes-vm@.service
%{_unitdir}/qubes-reload-firewall@.service
%{_unitdir}/qubes-reload-firewall@.timer
%attr(2770,root,qubes) %dir /var/lib/qubes
%attr(2770,root,qubes) %dir /var/lib/qubes/vm-templates
%attr(2770,root,qubes) %dir /var/lib/qubes/appvms
%attr(2770,root,qubes) %dir /var/lib/qubes/servicevms
%attr(2770,root,qubes) %dir /var/lib/qubes/backup
%attr(2770,root,qubes) %dir /var/lib/qubes/dvmdata
%attr(2770,root,qubes) %dir /var/lib/qubes/vm-kernels
/usr/share/qubes/vm-template.xml
/usr/share/qubes/vm-template-hvm.xml
/usr/lib/tmpfiles.d/qubes.conf
/usr/lib/qubes/qubes-prepare-saved-domain.sh
/usr/lib/qubes/qubes-update-dispvm-savefile-with-progress.sh
/etc/xen/scripts/block.qubes
/etc/xen/scripts/block-snapshot
/etc/xen/scripts/block-origin
/etc/xen/scripts/vif-route-qubes
%attr(0664,root,qubes) %config(noreplace) /etc/qubes-rpc/policy/qubes.Filecopy
%attr(0664,root,qubes) %config(noreplace) /etc/qubes-rpc/policy/qubes.GetImageRGBA
%attr(0664,root,qubes) %config(noreplace) /etc/qubes-rpc/policy/qubes.OpenInVM
%attr(0664,root,qubes) %config(noreplace) /etc/qubes-rpc/policy/qubes.OpenURL
%attr(0664,root,qubes) %config(noreplace) /etc/qubes-rpc/policy/qubes.NotifyTools
%attr(0664,root,qubes) %config(noreplace) /etc/qubes-rpc/policy/qubes.NotifyUpdates
%attr(0664,root,qubes) %config(noreplace) /etc/qubes-rpc/policy/qubes.VMShell
%attr(0664,root,qubes) %config(noreplace) /etc/qubes-rpc/policy/qubes.GetRandomizedTime
/etc/qubes-rpc/qubes.NotifyTools
/etc/qubes-rpc/qubes.NotifyUpdates
/etc/qubes-rpc/qubes.GetRandomizedTime
%attr(2770,root,qubes) %dir /var/log/qubes
%attr(0770,root,qubes) %dir /var/run/qubes
/etc/xdg/autostart/qubes-guid.desktop
