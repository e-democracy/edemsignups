# coding=utf-8
from google.appengine.ext import db

# clone_entity is from http://stackoverflow.com/questions/2687724/copy-an-entity-in-google-app-engine-datastore-in-python-without-knowing-property/7532887#7532887
def clone_entity(e, skip_auto_now=False, skip_auto_now_add=False, **extra_args):
  """Clones an entity, adding or overriding constructor attributes.

  The cloned entity will have exactly the same property values as the original
  entity, except where overridden. By default it will have no parent entity or
  key name, unless supplied.

  Args:
    e: The entity to clone
    skip_auto_now: If True then all DateTimeProperty propertes will be skipped 
                    which have the 'auto_now' flag set to True
    skip_auto_now_add: If True then all DateTimeProperty propertes will be 
                        skipped which have the 'auto_now_add' flag set to True
    extra_args: Keyword arguments to override from the cloned entity and pass
      to the constructor.
  Returns:
    A cloned, possibly modified, copy of entity e.
  """

  klass = e.__class__
  props = {}
  for k, v in klass.properties().iteritems():
    if not (type(v) == db.DateTimeProperty and ((skip_auto_now and 
                getattr(v, 'auto_now')) or 
                (skip_auto_now_add and getattr(v, 'auto_now_add')))):
      if type(v) == db.ReferenceProperty:
        value = getattr(klass, k).get_value_for_datastore(self)
      else:
        value = v.__get__(e, klass)
      props[k] = value
  props.update(extra_args)
  return klass(**props)
