# coding=utf-8

import sys, os                                                                  
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),       
                '../lib'))  

# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages  
try:                                                                            
    __import__('pkg_resources').declare_namespace(__name__)                     
except ImportError:                                                             
    from pkgutil import extend_path                                             
    __path__ = extend_path(__path__, __name__)  
