import os
import unittest
from unittest.mock import patch

class MarketRoutingTests(unittest.TestCase):
    def test_complete_json_with_only_extra_closing_brace_is_logged_normalization(self):
        from core import parse_market_json
        value,note=parse_market_json('{"x":"literal }}"}}')
        self.assertEqual(value,{'x':'literal }}'})
        self.assertTrue(note)
    def test_json_normalization_never_merges_two_answers_or_discards_prose(self):
        from core import parse_market_json
        for text in ['{"x":1}{"x":2}','{"x":1} explanation','{"x":,"y":2}']:
            with self.assertRaises(ValueError):parse_market_json(text)
    def test_gpt_oss_prompt_json_removes_decoder_format_but_keeps_schema(self):
        from core import market_output_request
        schema={'type':'object','properties':{'x':{'type':'string'}}}
        settings={'response_format':{'type':'json_schema','json_schema':{'schema':schema}},'max_tokens':123}
        with patch.dict(os.environ,{'GRAPH_API_PROVIDER':'market'},clear=True):
            system,config,mode=market_output_request('gpt-oss-120b','original',settings)
        self.assertNotIn('response_format',config)
        self.assertIn('original',system);self.assertIn('"x"',system)
        self.assertEqual(mode,'prompt_json')
        self.assertIn('response_format',settings)
    def test_non_market_request_preserves_native_format(self):
        from core import market_output_request
        settings={'response_format':{'type':'json_object'}}
        with patch.dict(os.environ,{},clear=True):
            system,config,mode=market_output_request('gpt-oss-120b','original',settings)
        self.assertEqual((system,config,mode),('original',settings,'native'))
    def test_market_routes_all_stages_and_removes_provider_specific_options(self):
        from core import api_target
        with patch.dict(os.environ,{'GRAPH_API_PROVIDER':'market','MARKET_API_BASE':'https://market.example/v1','MARKET_API_KEY':'secret','GRAPH_MODEL_OVERRIDE':'gpt-oss-120b'},clear=True):
            model,base,key,settings=api_target('old-warrant-model',{'chat_template_kwargs':{},'max_tokens':6144})
        self.assertEqual((model,base,key),('gpt-oss-120b','https://market.example/v1','secret'))
        self.assertEqual(settings,{'max_tokens':6144})
    def test_default_nvidia_route_is_preserved(self):
        from core import api_target
        with patch.dict(os.environ,{'NVIDIA_BASE_URL':'https://nvidia.example/v1','NVIDIA_API_KEY':'key'},clear=True):
            self.assertEqual(api_target('m',{})[:3],('m','https://nvidia.example/v1','key'))
