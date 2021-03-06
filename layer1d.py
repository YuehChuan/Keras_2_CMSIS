#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 10 15:30:39 2019

@author: quinn
"""

from copy import deepcopy

from layer import layer


class Conv1d(layer):
    c_function = 'arm_convolve_HWC_q7_basic_1d'

    def opt(self,mode='basic'):
        self.c_function = 'arm_convolve_HWC_q7_basic_1d'
        if 'fast' in mode:
            if (self.input_shape[-1] %4 == 0 or self.output_shape[-1]%2 == 0):
                self.c_function = 'arm_convolve_HWC_q7_fast_1d'
            else:
                print("attempted to optimize",self.name,"but encountered unsupported shape, reverting to basic")
        elif 'q15' in mode:
            self.c_function = 'arm_convolve_HWC_q15_basic_1d'

    def p_def(self):
        return '\n\n'.join([self.p_kern(), self.p_bias()]) + '\n\n'
        

    def p_func_call(self, sig='_needs_source_', dst='_needs_dest_', bufA='_needs_buf_A', bufB='_needs_buf_B', length=-1, **args):
        length = self.size_check(length,True)
        foo = [sig, self.input_shape[-2], self.input_shape[-1], 
                self.name+'_KERN', 
                self.config['filters'], 
                self.config['kernel_size'], 
                self.config['padding'],
                self.config['strides'],
                self.name+'_BIAS',
                0, # self.bias_shift,
                0, # self.out_shift,
                dst, bufA, bufB]

        return  self.c_function + '('+', '.join([ str(a) for a in foo])+');\n'
    
    def get_buf_size(self,length=-1):
        if isinstance(length,str):
            return self.config['kernel_size'][0]-1
        length = self.size_check(length)
        return length+self.config['kernel_size'][0]-1
    
    def set_output_shape(self):
        self.output_shape = deepcopy(self.input_shape)
        self.output_shape[1] = self.config['filters']

    def __p_macro(self,name,array):
        pos = ['WINDOW','INPUT','OUTPUT']
        out = ''
        for i,s in enumerate(array.shape):
            out += '#define ' + '_'.join([self.name.upper(),'SIZE',name.upper(), pos[i]]) + ' (%d)\n' % (s) ;
        return out;

    def p_macro(self):
        out = ''
        if (self.weights is None): return ''
        Index = list(self.weights.keys())
        if len(Index) == 0: return ''
        index = Index[0]
        for k in self.weights[index].keys():
            if 'bias' in k:
                out += self._p_macro('BIAS', self.weights[index][k])
            if 'kern' in k:
                out += self.__p_macro('KERN', self.weights[index][k])
        return out
    
    def get_bufA_size(self):
        return 2*self.input_shape[-1]*self.input_shape[-1]*self.input_shape[-1]

class Max_pool1d(layer):
    c_function = 'arm_maxpool_q7_HWC_1d'
    
    def p_func_call(self, sig='_needs_source_', dst='_needs_dest_',length=-1, **args):
        length = self.size_check(length, True)
        foo = [sig, str(self.config['pool_size'][0]), str(self.output_shape[1]), dst, str(length)]
        out = self.c_function + '('+', '.join(foo)+');\n'
        if isinstance(length,str):
            out += length + ' /= ' + str(self.config['pool_size'][0]) + ';\n'
        return out;
    
    def set_output_shape(self):
        self.output_shape = deepcopy(self.input_shape)
        if self.output_shape[0] is not None:
            self.output_shape[0] = self.output_shape[0] // self.config['pool_size'][0]

class Ave_pool1d(Max_pool1d):
    c_function = 'arm_avepool_q7_HWC_1d'

class Up_sample1d(layer):
    c_function = 'arm_upsample_q7_HWC_1d'
    
    def p_func_call(self, sig='_needs_source_', dst='_needs_dest_',length=-1, **args):
        length = self.size_check(length, True)
        foo = [sig, str(self.config['size']), str(self.output_shape[1]), dst, str(length)]
        out = self.c_function + '('+', '.join(foo)+');\n'
        if isinstance(length,str):
            out += length + ' *= ' + str(self.config['size']) + ';\n'
        return out;
    
    def set_output_shape(self):
        self.output_shape = deepcopy(self.input_shape)
        if self.output_shape[0] is not None:
            self.output_shape[0] *= self.config['size']
        