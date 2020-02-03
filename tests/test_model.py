import datetime
import unittest

from ceph_bootstrap.config.model import CephSaltConfigModel, ModelStoreListener, ModelLoadListener


class StoreListener(ModelStoreListener):
    def __init__(self):
        self.called = False
        self.times_called = 0
        self.new_value = None
        self.timestamp = None

    def model_store(self, new_value):
        self.timestamp = datetime.datetime.utcnow()
        self.called = True
        self.times_called += 1
        self.new_value = new_value


class LoadListener(ModelLoadListener):
    def __init__(self, value):
        self.value = value
        self.called = False
        self.timestamp = None

    def model_load(self):
        self.timestamp = datetime.datetime.utcnow()
        self.called = True
        return self.value


class ModelTest(unittest.TestCase):
    def setUp(self):
        super(ModelTest, self).setUp()
        self.model = CephSaltConfigModel()

    def test_set_item1(self):
        self.model['key1'] = 'hello'
        self.assertIn('key1', self.model.model_tree)
        self.assertEqual(self.model.model_tree['key1'], 'hello')

    def test_set_item2(self):
        self.model['key1:key2'] = 'hello'
        self.assertIn('key1', self.model.model_tree)
        self.assertIn('key2', self.model.model_tree['key1'])
        self.assertEqual(self.model.model_tree['key1']['key2'], 'hello')

    def test_set_item_error1(self):
        with self.assertRaises(KeyError):
            self.model[''] = 'hello'

    def test_set_item_error2(self):
        with self.assertRaises(ValueError):
            self.model[['key']] = 'hello'

    def test_set_item_error3(self):
        self.model['key1'] = 'hello'
        with self.assertRaises(ValueError):
            self.model['key1:key2'] = 'hello'

    def test_get_item1(self):
        self.model['key1'] = 'hello'
        val = self.model['key1']
        self.assertEqual(val, 'hello')

    def test_get_item2(self):
        self.model['key1:key2'] = 'hello'
        val = self.model['key1:key2']
        self.assertEqual(val, 'hello')

    def test_get_item3(self):
        self.model['key1'] = {}
        self.model['key1:key2'] = 'hello'
        val = self.model['key1:key2']
        self.assertEqual(val, 'hello')

    def test_get_item_error1(self):
        with self.assertRaises(KeyError):
            val = self.model['']  # pylint: disable=unused-variable

    def test_get_item_error2(self):
        with self.assertRaises(ValueError):
            val = self.model[['key1']]  # pylint: disable=unused-variable

    def test_get_item_error3(self):
        self.model['key1'] = 'hello'
        with self.assertRaises(ValueError):
            val = self.model['key1:key2']  # pylint: disable=unused-variable

    def test_get_item_error4(self):
        self.model['key1:key2'] = 'hello'
        with self.assertRaises(KeyError):
            val = self.model['key1:key3']  # pylint: disable=unused-variable

    def test_model_listener(self):
        listener = StoreListener()
        self.model.add_listener(listener, "key1:key2")
        self.model['key1:key2'] = 'hello'
        self.assertTrue(listener.called)
        self.assertEqual(listener.times_called, 1)
        self.assertEqual(listener.new_value, 'hello')

    def test_model_listener2(self):
        listener = StoreListener()
        root_listener = StoreListener()
        self.model.add_listener(listener, "key1")
        self.model['key1:key2'] = 'hello'
        self.model.add_listener(root_listener)
        self.assertTrue(listener.called)
        # listener is called twice because it is first called with {}
        # and then with {'key2': 'world}
        self.assertEqual(listener.times_called, 2)
        self.model['key1']['key2'] = 'world'
        self.assertTrue(listener.called)
        self.assertEqual(listener.times_called, 3)
        self.assertEqual(listener.new_value, {'key2': 'world'})
        self.assertTrue(root_listener.called)
        self.assertEqual(root_listener.new_value, {'key1': {'key2': 'world'}})

    def test_model_two_listeners(self):
        listener1 = StoreListener()
        listener2 = StoreListener()
        self.model.add_listener(listener1, "key1:key2")
        self.model.add_listener(listener2, "key1:key2")
        self.model['key1:key2'] = 'hello'
        self.assertTrue(listener1.called)
        self.assertEqual(listener1.new_value, 'hello')
        self.assertTrue(listener2.called)
        self.assertEqual(listener2.new_value, 'hello')
        self.assertGreaterEqual(listener2.timestamp, listener1.timestamp)

    def test_model_listener_ancestor_node(self):
        listener1 = StoreListener()
        listener2 = StoreListener()
        self.model['key1:key1.1:key1.1.1'] = 'hello'
        self.model['key1:key1.1:key1.1.2'] = 'world'
        self.model.add_listener(listener1, "key1:key1.1:key1.1.1")
        self.model.add_listener(listener2, "key1:key1.1")
        self.model['key1:key1.1:key1.1.1'] = 'hello2'
        self.assertTrue(listener1.called)
        self.assertEqual(listener1.new_value, 'hello2')
        self.assertTrue(listener2.called)
        self.assertDictEqual(listener2.new_value, {'key1.1.1': 'hello2', 'key1.1.2': 'world'})
        listener1.called = False
        listener2.called = False
        self.model['key1:key1.1:key1.1.2'] = 'world2'
        self.assertFalse(listener1.called)
        self.assertTrue(listener2.called)
        self.assertDictEqual(listener2.new_value, {'key1.1.1': 'hello2', 'key1.1.2': 'world2'})

    def test_model_in_operator(self):
        self.model['key1:key2'] = 'hello'
        self.assertIn('key1', self.model)
        self.assertNotIn('key2', self.model)
        self.assertIn('key1:key2', self.model)
        self.assertNotIn('key1:key3', self.model)
        with self.assertRaises(ValueError):
            if 'key1:key2:key3' in self.model:
                pass

    def test_model_in_operator_error1(self):
        with self.assertRaises(KeyError):
            if '' in self.model:
                pass

    def test_model_in_operator_error2(self):
        with self.assertRaises(ValueError):
            if ['hello'] in self.model:
                pass

    def test_model_list(self):
        listener = StoreListener()
        self.model.add_listener(listener, 'key1:key2')
        self.model['key1:key2'] = []
        self.assertTrue(listener.called)
        self.assertEqual(listener.times_called, 1)
        self.assertListEqual(listener.new_value, [])
        self.model['key1:key2'].append('hello')
        self.assertEqual(listener.times_called, 2)
        self.assertListEqual(listener.new_value, ['hello'])
        lst = self.model['key1:key2']
        lst.insert(0, 'world')
        self.assertEqual(len(lst), 2)
        self.assertListEqual(lst, ['world', 'hello'])
        self.assertEqual(listener.times_called, 3)
        self.assertListEqual(listener.new_value, ['world', 'hello'])
        lst.pop(1)
        self.assertEqual(listener.times_called, 4)
        self.assertListEqual(listener.new_value, ['world'])
        lst.remove('world')
        self.assertEqual(listener.times_called, 5)
        self.assertListEqual(listener.new_value, [])
        lst.insert(0, 'world')
        lst.clear()
        self.assertEqual(listener.times_called, 7)
        self.assertListEqual(listener.new_value, [])

    def test_model_inner_dict(self):
        listener = StoreListener()
        self.model.add_listener(listener, 'key1:key2')
        self.model['key1'] = {'key2': 'hello'}
        self.assertTrue(listener.called)
        self.assertEqual(listener.times_called, 1)
        self.assertEqual(listener.new_value, 'hello')

    def test_model_inner_dict2(self):
        listener1 = StoreListener()
        listener2 = StoreListener()
        self.model.add_listener(listener1, 'key1:key2')
        self.model.add_listener(listener2, 'key1:key2:key3')
        self.model['key1'] = {'key2': {'key3': 'hello'}}
        self.assertTrue(listener1.called)
        self.assertEqual(listener1.times_called, 2)
        self.assertDictEqual(listener1.new_value, {'key3': 'hello'})
        self.assertTrue(listener2.called)
        self.assertEqual(listener2.times_called, 1)
        self.assertEqual(listener2.new_value, 'hello')

    def test_model_root_load(self):
        listener = LoadListener({'hello': 'world'})
        self.model.add_listener(listener)
        self.assertEqual(self.model['hello'], 'world')

    def test_model_leaf_dict_load(self):
        listener = LoadListener({'hello': 'world'})
        listener2 = StoreListener()
        self.model.add_listener(listener, 'key1')
        self.model.add_listener(listener2, 'key1:hello')
        self.assertEqual(self.model['key1:hello'], 'world')
        self.assertFalse(listener2.called)
        self.model['key1']['hello'] = 'world2'
        self.assertTrue(listener2.called)
        self.assertEqual(listener2.times_called, 1)
        self.assertEqual(listener2.new_value, 'world2')

    def test_model_inner_dict_load(self):
        listener = LoadListener({'key2': {'hello': 'world'}})
        listener2 = StoreListener()
        self.model.add_listener(listener, 'key1')
        self.model.add_listener(listener2, 'key1:key2')
        val = self.model['key1:key2:hello']
        self.assertEqual(val, 'world')
        self.assertFalse(listener2.called)
        self.model['key1:key2']['hello'] = 'world2'
        self.assertTrue(listener2.called)
        self.assertEqual(listener2.times_called, 1)
        self.assertEqual(listener2.new_value, {'hello': 'world2'})

    def test_model_list_load(self):
        listener = LoadListener(['hello'])
        listener2 = StoreListener()
        self.model.add_listener(listener, 'key1')
        self.model.add_listener(listener2, 'key1')
        self.model['key1'].append('world')
        self.assertTrue(listener2.called)
        self.assertEqual(listener2.times_called, 1)
        self.assertListEqual(listener2.new_value, ['hello', 'world'])

    def test_model_inner_list_load(self):
        listener = LoadListener({'key2': ['hello']})
        listener2 = StoreListener()
        self.model.add_listener(listener, 'key1')
        self.model.add_listener(listener2, 'key1:key2')
        self.model['key1:key2'].append('world')
        self.assertTrue(listener2.called)
        self.assertEqual(listener2.times_called, 1)
        self.assertListEqual(listener2.new_value, ['hello', 'world'])
