from malcolm.core import StringMeta, Widget, Alarm, AlarmSeverity, Part
from malcolm.modules.builtin import hooks, infos, parts
from malcolm import version
from malcolm.modules.ca.util import catools

import os
import subprocess
from annotypes import Anno

malcolm_logo_svg = """\
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!-- Created with Inkscape (http://www.inkscape.org/) -->

<svg
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:cc="http://creativecommons.org/ns#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:xlink="http://www.w3.org/1999/xlink"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   width="50px"
   height="50px"
   id="svg5202"
   version="1.1"
   inkscape:version="0.47 r22583"
   sodipodi:docname="logo3.svg">
  <defs
     id="defs5204">
    <linearGradient
       id="linearGradient6024">
      <stop
         style="stop-color:#00d900;stop-opacity:1;"
         offset="0"
         id="stop6026" />
      <stop
         style="stop-color:#000000;stop-opacity:1;"
         offset="1"
         id="stop6028" />
    </linearGradient>
    <linearGradient
       id="linearGradient6016">
      <stop
         style="stop-color:#ffff00;stop-opacity:1;"
         offset="0"
         id="stop6018" />
      <stop
         style="stop-color:#000000;stop-opacity:1;"
         offset="1"
         id="stop6020" />
    </linearGradient>
    <linearGradient
       id="linearGradient6008">
      <stop
         style="stop-color:#ff0000;stop-opacity:1;"
         offset="0"
         id="stop6010" />
      <stop
         style="stop-color:#000000;stop-opacity:1;"
         offset="1"
         id="stop6012" />
    </linearGradient>
    <linearGradient
       id="linearGradient6000">
      <stop
         style="stop-color:#0505ff;stop-opacity:1;"
         offset="0"
         id="stop6002" />
      <stop
         style="stop-color:#000000;stop-opacity:1;"
         offset="1"
         id="stop6004" />
    </linearGradient>
    <inkscape:perspective
       sodipodi:type="inkscape:persp3d"
       inkscape:vp_x="0 : 16 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_z="32 : 16 : 1"
       inkscape:persp3d-origin="16 : 10.666667 : 1"
       id="perspective5210" />
    <inkscape:perspective
       id="perspective5732"
       inkscape:persp3d-origin="0.5 : 0.33333333 : 1"
       inkscape:vp_z="1 : 0.5 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_x="0 : 0.5 : 1"
       sodipodi:type="inkscape:persp3d" />
    <inkscape:perspective
       id="perspective5758"
       inkscape:persp3d-origin="0.5 : 0.33333333 : 1"
       inkscape:vp_z="1 : 0.5 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_x="0 : 0.5 : 1"
       sodipodi:type="inkscape:persp3d" />
    <inkscape:perspective
       id="perspective5758-5"
       inkscape:persp3d-origin="0.5 : 0.33333333 : 1"
       inkscape:vp_z="1 : 0.5 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_x="0 : 0.5 : 1"
       sodipodi:type="inkscape:persp3d" />
    <inkscape:perspective
       id="perspective5758-7"
       inkscape:persp3d-origin="0.5 : 0.33333333 : 1"
       inkscape:vp_z="1 : 0.5 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_x="0 : 0.5 : 1"
       sodipodi:type="inkscape:persp3d" />
    <inkscape:perspective
       id="perspective5758-71"
       inkscape:persp3d-origin="0.5 : 0.33333333 : 1"
       inkscape:vp_z="1 : 0.5 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_x="0 : 0.5 : 1"
       sodipodi:type="inkscape:persp3d" />
    <inkscape:perspective
       id="perspective5825"
       inkscape:persp3d-origin="0.5 : 0.33333333 : 1"
       inkscape:vp_z="1 : 0.5 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_x="0 : 0.5 : 1"
       sodipodi:type="inkscape:persp3d" />
    <inkscape:perspective
       id="perspective5825-0"
       inkscape:persp3d-origin="0.5 : 0.33333333 : 1"
       inkscape:vp_z="1 : 0.5 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_x="0 : 0.5 : 1"
       sodipodi:type="inkscape:persp3d" />
    <inkscape:perspective
       id="perspective5825-6"
       inkscape:persp3d-origin="0.5 : 0.33333333 : 1"
       inkscape:vp_z="1 : 0.5 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_x="0 : 0.5 : 1"
       sodipodi:type="inkscape:persp3d" />
    <inkscape:perspective
       id="perspective5825-61"
       inkscape:persp3d-origin="0.5 : 0.33333333 : 1"
       inkscape:vp_z="1 : 0.5 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_x="0 : 0.5 : 1"
       sodipodi:type="inkscape:persp3d" />
    <linearGradient
       inkscape:collect="always"
       xlink:href="#linearGradient6000"
       id="linearGradient6006"
       x1="6.7470002"
       y1="27.253048"
       x2="0.5"
       y2="4.7470002"
       gradientUnits="userSpaceOnUse" />
    <linearGradient
       inkscape:collect="always"
       xlink:href="#linearGradient6008"
       id="linearGradient6014"
       x1="25.253"
       y1="27.253048"
       x2="31.5"
       y2="4.7469516"
       gradientUnits="userSpaceOnUse" />
    <linearGradient
       inkscape:collect="always"
       xlink:href="#linearGradient6016"
       id="linearGradient6022"
       x1="6.9657598"
       y1="10.040453"
       x2="11.25"
       y2="16"
       gradientUnits="userSpaceOnUse" />
    <linearGradient
       inkscape:collect="always"
       xlink:href="#linearGradient6024"
       id="linearGradient6030"
       x1="24.921328"
       y1="9.7980118"
       x2="20.75"
       y2="16"
       gradientUnits="userSpaceOnUse" />
    <inkscape:perspective
       id="perspective6055"
       inkscape:persp3d-origin="0.5 : 0.33333333 : 1"
       inkscape:vp_z="1 : 0.5 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_x="0 : 0.5 : 1"
       sodipodi:type="inkscape:persp3d" />
    <inkscape:perspective
       id="perspective6055-5"
       inkscape:persp3d-origin="0.5 : 0.33333333 : 1"
       inkscape:vp_z="1 : 0.5 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_x="0 : 0.5 : 1"
       sodipodi:type="inkscape:persp3d" />
    <inkscape:perspective
       id="perspective6055-6"
       inkscape:persp3d-origin="0.5 : 0.33333333 : 1"
       inkscape:vp_z="1 : 0.5 : 1"
       inkscape:vp_y="0 : 1000 : 0"
       inkscape:vp_x="0 : 0.5 : 1"
       sodipodi:type="inkscape:persp3d" />
  </defs>
  <sodipodi:namedview
     id="base"
     pagecolor="#ffffff"
     bordercolor="#666666"
     borderopacity="1.0"
     inkscape:pageopacity="0.0"
     inkscape:pageshadow="2"
     inkscape:zoom="15.836083"
     inkscape:cx="10.586625"
     inkscape:cy="6.02439"
     inkscape:current-layer="layer1"
     showgrid="true"
     inkscape:grid-bbox="true"
     inkscape:document-units="px"
     inkscape:window-width="1108"
     inkscape:window-height="890"
     inkscape:window-x="2588"
     inkscape:window-y="63"
     inkscape:window-maximized="0" />
  <metadata
     id="metadata5207">
    <rdf:RDF>
      <cc:Work
         rdf:about="">
        <dc:format>image/svg+xml</dc:format>
        <dc:type
           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />
        <dc:title />
      </cc:Work>
    </rdf:RDF>
  </metadata>
  <g
     id="layer1"
     inkscape:label="Layer 1"
     inkscape:groupmode="layer"
     transform="scale(1.5, 1.5)">
    <path
       style="color:#000000;fill:none;stroke:#000000;stroke-width:2.99999976000000013;stroke-linecap:square;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0;marker:none;visibility:visible;display:inline;overflow:visible;enable-background:accumulate"
       d="M 5.7469517,26.253048 C 3.1229678,23.629064 1.5,20.004064 1.5,16 1.5,11.995935 3.1230161,8.3709839 5.747,5.747"
       id="path5212"
       sodipodi:nodetypes="csc" />
    <path
       id="path5748"
       style="fill:none;stroke:#000000;stroke-width:3;stroke-linecap:square;stroke-linejoin:miter;stroke-opacity:1;stroke-miterlimit:4;stroke-dasharray:none"
       d="M 16,16 9.2824856,9.2824854 C 7.5633237,11.001647 6.5,13.376647 6.5,16 c 0,2.623352 1.0633237,4.998352 2.7824856,6.717514"
       sodipodi:nodetypes="ccsc" />
    <path
       id="path5996"
       style="fill:none;stroke:#000000;stroke-width:3;stroke-linecap:square;stroke-linejoin:miter;stroke-opacity:1;stroke-miterlimit:4;stroke-dasharray:none"
       d="M 22.717514,22.717514 C 24.436676,20.998353 25.5,18.623353 25.5,16 l 0,0 c 0,-2.623352 -1.063324,-4.998353 -2.782486,-6.7175145 L 16,16"
       sodipodi:nodetypes="ccccc" />
    <path
       style="color:#000000;fill:none;stroke:#000000;stroke-width:2.99999976000000013;stroke-linecap:square;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0;marker:none;visibility:visible;display:inline;overflow:visible;enable-background:accumulate"
       d="M 26.253,5.7469515 C 28.876984,8.3709355 30.5,11.995935 30.5,16 l 0,0 0,0 c 0,4.004064 -1.622968,7.629064 -4.246952,10.253048"
       id="path5867"
       sodipodi:nodetypes="ccccc" />
    <rect
       style="color:#000000;fill:#000000;fill-opacity:0.25098039000000000;stroke:#3c9ab0;stroke-width:0.99999987999999995;stroke-linecap:square;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:0.25098041;stroke-dasharray:none;stroke-dashoffset:0;marker:none;visibility:visible;display:inline;overflow:visible;enable-background:accumulate"
       id="rect6032-7"
       width="9"
       height="6"
       x="9.5"
       y="0.50000006"
       rx="0.99999982"
       ry="1" />
    <rect
       style="color:#000000;fill:#000000;fill-opacity:0.25098039000000000;stroke:#3c9ab0;stroke-width:1;stroke-linecap:square;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:0.25098041;stroke-dasharray:none;stroke-dashoffset:0;marker:none;visibility:visible;display:inline;overflow:visible;enable-background:accumulate"
       id="rect6032-1"
       width="10"
       height="6"
       x="1.5"
       y="15.5"
       rx="0.99999976"
       ry="1" />
    <rect
       style="color:#000000;fill:#000000;fill-opacity:0.25098039000000000;stroke:#3c9ab0;stroke-width:1;stroke-linecap:square;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:0.25098041;stroke-dasharray:none;stroke-dashoffset:0;marker:none;visibility:visible;display:inline;overflow:visible;enable-background:accumulate"
       id="rect6032"
       width="11"
       height="7"
       x="19.5"
       y="11.5"
       rx="0.99999994"
       ry="0.99999994" />
    <rect
       style="color:#000000;fill:#000000;fill-opacity:0.25098039000000000;stroke:#3c9ab0;stroke-width:0.99999994000000003;stroke-linecap:square;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:0.25098041;stroke-dasharray:none;stroke-dashoffset:0;marker:none;visibility:visible;display:inline;overflow:visible;enable-background:accumulate"
       id="rect6032-0"
       width="7"
       height="5"
       x="15.5"
       y="26.5"
       rx="0.99999988"
       ry="0.99999994" />
    <path
       sodipodi:nodetypes="csc"
       id="path3828"
       d="M 5.7469517,26.253048 C 3.1229678,23.629064 1.5,20.004064 1.5,16 1.5,11.995935 3.1230161,8.3709839 5.747,5.747"
       style="color:#000000;fill:none;stroke:url(#linearGradient6006);stroke-width:2;stroke-linecap:square;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0;marker:none;visibility:visible;display:inline;overflow:visible;enable-background:accumulate" />
    <path
       sodipodi:nodetypes="ccsc"
       d="M 16,16 9.2824856,9.2824854 C 7.5633237,11.001647 6.5,13.376647 6.5,16 c 0,2.623352 1.0633237,4.998352 2.7824856,6.717514"
       style="fill:none;stroke:url(#linearGradient6022);stroke-width:2;stroke-linecap:square;stroke-linejoin:miter;stroke-opacity:1;stroke-miterlimit:4;stroke-dasharray:none"
       id="path3830" />
    <path
       sodipodi:nodetypes="ccccc"
       d="M 22.717514,22.717514 C 24.436676,20.998353 25.5,18.623353 25.5,16 l 0,0 c 0,-2.623352 -1.063324,-4.998353 -2.782486,-6.7175145 L 16,16"
       style="fill:none;stroke:url(#linearGradient6030);stroke-width:2;stroke-linecap:square;stroke-linejoin:miter;stroke-opacity:1;stroke-miterlimit:4;stroke-dasharray:none"
       id="path3832" />
    <path
       sodipodi:nodetypes="ccccc"
       id="path3834"
       d="M 26.253,5.7469515 C 28.876984,8.3709355 30.5,11.995935 30.5,16 l 0,0 0,0 c 0,4.004064 -1.622968,7.629064 -4.246952,10.253048"
       style="color:#000000;fill:none;stroke:url(#linearGradient6014);stroke-width:2;stroke-linecap:square;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0;marker:none;visibility:visible;display:inline;overflow:visible;enable-background:accumulate" />
  </g>
</svg>
"""

not_malcolm_logo_svg = """\
<iframe id="ytplayer" type="text/html" width="100" height="100"
  src="https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&origin=http://localhost"
  frameborder="0"></iframe>
"""

def start_ioc(stats, prefix):
    db_macros = "prefix='%s'" % prefix
    epics_base = None
    try:
        epics_base = os.environ["EPICS_BASE"]
    except KeyError:
        epics_base = "/dls_sw/epics/R3.14.12.7/base"
    softIoc_bin = epics_base + "/bin/linux-x86_64/softIoc"
    for key, value in stats.items():
        db_macros += ",%s='%s'" % (key, value)
    root = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]
    db_template = os.path.join(root, 'db', 'stats.template')
    ioc = subprocess.Popen(
        [softIoc_bin, "-m", db_macros, "-d", db_template],
        stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    # wait for IOC to start
    pid_rbv = catools.caget("%s:PID" % prefix, timeout=5)
    if int(pid_rbv) != os.getpid():
        raise Exception("Got back different PID: " +
                        "is there another stats instance on the machine?")
    catools.caput("%s:YAML:PATH" % prefix, stats["yaml_path"],
                  datatype=catools.DBR_CHAR_STR)
    catools.caput("%s:PYMALCOLM:PATH" % prefix, stats["pymalcolm_path"],
                  datatype=catools.DBR_CHAR_STR)
    return ioc


def parse_yaml_version(file_path, work_area, prod_area):
    ver = "unknown"
    if file_path.startswith(work_area):
        ver = "Work"
    elif file_path.startswith(prod_area):
        cwd = os.getcwd()
        os.chdir(os.path.split(file_path)[0])
        try:
            ver = subprocess.check_output(
                ['/usr/bin/git', 'describe',
                 '--tags', '--exact-match']).strip(b'\n').decode("utf-8")
        except subprocess.CalledProcessError:
            ver = "Prod (unknown version)"
            print("Git error when parsing yaml version")

        os.chdir(cwd)
    return ver


with Anno("prefix for self.stats PVs"):
    APvPrefix = str


class StatsPart(Part):
    def __init__(self, name, prefix):
        # type: (parts.APartName, APvPrefix,) -> None
        super(StatsPart, self).__init__(name)
        self.ioc = None
        self.prefix = prefix
        self.stats = dict()
        cwd = os.getcwd()
        sys_call_bytes = open('/proc/%s/cmdline' % os.getpid(),
                              'rb').read().split(
            b'\0')
        sys_call = [el.decode("utf-8") for el in sys_call_bytes]
        if sys_call[1].startswith('/'):
            self.stats["pymalcolm_path"] = sys_call[1]
        else:
            self.stats["pymalcolm_path"] = os.path.join(cwd, sys_call[1])

        if sys_call[2].startswith('/'):
            self.stats["yaml_path"] = sys_call[2]
        else:
            self.stats["yaml_path"] = os.path.join(cwd, sys_call[2])

        self.stats["yaml_ver"] = parse_yaml_version(self.stats["yaml_path"],
                                                    '/dls_sw/work',
                                                    '/dls_sw/prod')

        if self.stats["pymalcolm_path"].startswith('/dls_sw/prod'):
            self.stats["pymalcolm_ver"] = version.__version__
        else:
            self.stats["pymalcolm_ver"] = "Work"
        hostname = os.uname()[1]
        self.stats["kernel"] = "%s %s" % (os.uname()[0], os.uname()[2])
        self.stats["hostname"] = hostname if len(hostname) < 39 else hostname[
                                                                     :35] + '...'
        self.stats["pid"] = os.getpid()

        self.pymalcolm_path = StringMeta(
            "Path to pymalcolm executable",
            tags=[Widget.MULTILINETEXTUPDATE.tag()]).create_attribute_model(
            self.stats["pymalcolm_path"])
        self.pymalcolm_ver = StringMeta(
            "Version of pymalcolm executable",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            self.stats["pymalcolm_ver"])
        self.yaml_path = StringMeta(
            "Path to yaml configuration file",
            tags=[Widget.MULTILINETEXTUPDATE.tag()]).create_attribute_model(
            self.stats["yaml_path"])
        self.yaml_ver = StringMeta(
            "version of yaml configuration file",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            self.stats["yaml_ver"])
        self.hostname = StringMeta(
            "Name of host machine",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            self.stats["hostname"])
        self.kernel = StringMeta(
            "Kernel of host machine",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            self.stats["kernel"])
        self.pid = StringMeta(
            "process ID of pymalcolm instance",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            self.stats["pid"])

        self.logo = StringMeta(
            "block logo", [Widget.ICON.tag()]).create_attribute_model(
            malcolm_logo_svg)

    def start_ioc(self):
        if self.ioc is None:
            self.ioc = start_ioc(self.stats, self.prefix)

    def stop_ioc(self):
        if self.ioc is not None:
            self.ioc.terminate()
            self.ioc = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(StatsPart, self).setup(registrar)
        registrar.add_attribute_model("pymalcolmPath", self.pymalcolm_path)
        registrar.add_attribute_model("pymalcolmVer", self.pymalcolm_ver)
        registrar.add_attribute_model("yamlPath", self.yaml_path)
        registrar.add_attribute_model("yamlVer", self.yaml_ver)
        registrar.add_attribute_model("hostname", self.hostname)
        registrar.add_attribute_model("kernel", self.kernel)
        registrar.add_attribute_model("pid", self.pid)

        if self.stats["yaml_ver"] in ["Work", "unknown"]:
            message = "Non-prod YAML config"
            alarm = Alarm(message=message, severity=AlarmSeverity.MINOR_ALARM)
            registrar.report(infos.HealthInfo(alarm))

        registrar.add_attribute_model("logo", self.logo)

        registrar.hook(hooks.InitHook, self.start_ioc)

        registrar.hook(hooks.HaltHook, self.stop_ioc)
