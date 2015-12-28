#!/usr/bin/env python

# Copyright 2015 Ben Vanik & shuffle2. All Rights Reserved.

"""PPC instruction table generator.

Generates various headers/sources for looking up and handling PPC instructions.

This is based on shuffle2's PPC generator:
https://gist.github.com/shuffle2/10015968
"""

__author__ = 'ben.vanik@gmail.com (Ben Vanik)'

import os
import sys
from xml.etree.ElementTree import ElementTree, Element, SubElement, tostring, dump


self_path = os.path.dirname(os.path.abspath(__file__))


class Insn:
  pass


def bit_extract(x, leftmost, rightmost):
  return (x >> (32 - 1 - rightmost)) & ((1 << (rightmost - leftmost + 1)) - 1)


extended_opcode_bits = {
    'X': [(21, 30)],
    'XL': [(21, 30)],
    'XFX': [(21, 30)],
    'XFL': [(21, 30)],
    'VX': [(21, 31)],
    'VX128': [(22, 25), (27, 27)],
    'VX128_1': [(21, 27), (30, 31)],
    'VX128_2': [(22, 22), (27, 27)],
    'VX128_3': [(21, 27)],
    'VX128_4': [(21, 23), (26, 27)],
    'VX128_5': [(27, 27)],
    'VX128_R': [(22, 24), (27, 27)],
    'VX128_P': [(21, 22), (26, 27)],
    'VC': [(22, 31)],
    'VA': [(26, 31)],
    'XO': [(22, 30)],
    'XW': [(25, 30)],
    'A': [(26, 30)],
    'DS': [(30, 31)],
    'MD': [(27, 30)],
    'MDS': [(27, 30)],
    'MDSH': [(27, 29)],
    'XS': [(21, 29)],
    'DCBZ': [(6, 10), (21, 30)],  # like X
    }


def opcode_primary(insn):
  return bit_extract(insn, 0, 5)


def opcode_extended(insn, form):
  if form in extended_opcode_bits:
    parts = extended_opcode_bits[form]
    value = 0
    shift = 0
    for part in parts:
      shift = max(shift, part[1])
    for part in parts:
      part_value = bit_extract(insn, part[0], part[1])
      value = value | (part_value << (shift - part[1]))
    return value
  else:
    return -1


def parse_insns(filename):
  root = ElementTree(file = filename)
  insns = []
  # Convert to python types
  for e in root.findall('.//insn'):
    i = Insn()
    i.opcode = int(e.attrib['opcode'], 16)
    i.mnem = e.attrib['mnem']
    i.form = e.attrib['form']
    i.subform = e.attrib['sub-form']
    i.group = e.attrib['group']
    i.desc = e.attrib['desc']
    i.type = 'General'
    if 'sync' in e.attrib and e.attrib['sync'] == 'true':
      i.type = 'Sync'
    i.op_primary = opcode_primary(i.opcode)
    i.op_extended = opcode_extended(i.opcode, i.form)
    insns.append(i)
  return insns


def c_mnem(x):
  return x.replace('.', 'x')


def c_subform(x):
  x = x.replace('-', '_')
  if x[0] >= '0' and x[0] <= '9':
    x = '_' + x
  return x


def c_group(x):
  return 'k' + x[0].upper() + x[1:]


def c_bool(x):
  return 'true' if x else 'false'


def generate_opcodes(insns):
  l = []
  TAB = ' ' * 2
  def w0(x): l.append(x)
  def w1(x): w0(TAB * 1 + x)
  def w2(x): w0(TAB * 2 + x)
  def w3(x): w0(TAB * 3 + x)

  w0('// This code was autogenerated by %s. Do not modify!' % (sys.argv[0]))
  w0('// clang-format off')
  w0('#ifndef XENIA_CPU_PPC_PPC_OPCODE_H_')
  w0('#define XENIA_CPU_PPC_PPC_OPCODE_H_')
  w0('')
  w0('#include <cstdint>')
  w0('')
  w0('namespace xe {')
  w0('namespace cpu {')
  w0('namespace ppc {')
  w0('')

  for i in insns:
    i.mnem = c_mnem(i.mnem)
    i.subform = c_subform(i.subform)
  insns = sorted(insns, key = lambda i: i.mnem)

  w0('// All PPC opcodes in the same order they appear in ppc_opcode_table.h:')
  w0('enum class PPCOpcode : uint32_t {')
  for i in insns:
    w1('%s,' % (i.mnem))
  w1('kInvalid,')
  w0('};')

  w0('')
  w0('}  // namespace ppc')
  w0('}  // namespace cpu')
  w0('}  // namespace xe')
  w0('')
  w0('#endif  // XENIA_CPU_PPC_PPC_OPCODE_H_')
  w0('')

  return '\n'.join(l)


def generate_table(insns):
  l = []
  TAB = ' ' * 2
  def w0(x): l.append(x)
  def w1(x): w0(TAB * 1 + x)
  def w2(x): w0(TAB * 2 + x)
  def w3(x): w0(TAB * 3 + x)

  w0('// This code was autogenerated by %s. Do not modify!' % (sys.argv[0]))
  w0('// clang-format off')
  w0('#include <cstdint>')
  w0('')
  w0('#include "xenia/base/assert.h"')
  w0('#include "xenia/cpu/ppc/ppc_opcode.h"')
  w0('#include "xenia/cpu/ppc/ppc_opcode_info.h"')
  w0('')
  w0('namespace xe {')
  w0('namespace cpu {')
  w0('namespace ppc {')
  w0('')

  for i in insns:
    i.mnem = '"' + c_mnem(i.mnem) + '"'
    i.form = c_group(i.form)
    i.subform = c_subform(i.subform)
    i.desc = '"' + i.desc + '"'
    i.group = c_group(i.group)
    i.type = c_group(i.type)

  mnem_len = len(max(insns, key = lambda i: len(i.mnem)).mnem)
  form_len = len(max(insns, key = lambda i: len(i.form)).form)
  subform_len = len(max(insns, key = lambda i: len(i.subform)).subform)
  desc_len = len(max(insns, key = lambda i: len(i.desc)).desc)
  group_len = len(max(insns, key = lambda i: len(i.group)).group)
  type_len = len(max(insns, key = lambda i: len(i.type)).type)

  insns = sorted(insns, key = lambda i: i.mnem)

  w0('#define INSTRUCTION(opcode, mnem, form, subform, group, type, desc) \\')
  w0('    {opcode, mnem, PPCOpcodeFormat::form, PPCOpcodeGroup::group, PPCOpcodeType::type, desc, nullptr, nullptr}')
  w0('PPCOpcodeInfo ppc_opcode_table[] = {')
  fmt = 'INSTRUCTION(' + ', '.join([
      '0x%08x',
      '%-' + str(mnem_len) + 's',
      '%-' + str(form_len) + 's',
      '%-' + str(subform_len) + 's',
      '%-' + str(group_len) + 's',
      '%-' + str(type_len) + 's',
      '%-' + str(desc_len) + 's',
      ]) + '),'
  for i in insns:
    w1(fmt % (i.opcode, i.mnem, i.form, i.subform, i.group, i.type, i.desc))
  w0('};')
  w0('static_assert(sizeof(ppc_opcode_table) / sizeof(PPCOpcodeInfo) == static_cast<int>(PPCOpcode::kInvalid), "PPC table mismatch - rerun ppc-table-gen");')
  w0('')
  w0('const PPCOpcodeInfo& GetOpcodeInfo(PPCOpcode opcode) {')
  w1('return ppc_opcode_table[static_cast<int>(opcode)];')
  w0('}')
  w0('void RegisterOpcodeDisasm(PPCOpcode opcode, InstrDisasmFn fn) {')
  w1('assert_null(ppc_opcode_table[static_cast<int>(opcode)].disasm);')
  w1('ppc_opcode_table[static_cast<int>(opcode)].disasm = fn;')
  w0('}')
  w0('void RegisterOpcodeEmitter(PPCOpcode opcode, InstrEmitFn fn) {')
  w1('assert_null(ppc_opcode_table[static_cast<int>(opcode)].emit);')
  w1('ppc_opcode_table[static_cast<int>(opcode)].emit = fn;')
  w0('}')

  w0('')
  w0('}  // namespace ppc')
  w0('}  // namespace cpu')
  w0('}  // namespace xe')
  w0('')

  return '\n'.join(l)


def generate_lookup(insns):
  l = []
  TAB = ' ' * 2
  def w0(x): l.append(x)
  def w1(x): w0(TAB * 1 + x)
  def w2(x): w0(TAB * 2 + x)
  def w3(x): w0(TAB * 3 + x)

  for i in insns:
    i.mnem = c_mnem(i.mnem)

  w0('// This code was autogenerated by %s. Do not modify!' % (sys.argv[0]))
  w0('// clang-format off')
  w0('#include <cstdint>')
  w0('')
  w0('#include "xenia/base/assert.h"')
  w0('#include "xenia/cpu/ppc/ppc_opcode.h"')
  w0('#include "xenia/cpu/ppc/ppc_opcode_info.h"')
  w0('')
  w0('namespace xe {')
  w0('namespace cpu {')
  w0('namespace ppc {')
  w0('')
  w0('constexpr uint32_t ExtractBits(uint32_t v, uint32_t a, uint32_t b) {')
  w0('  return (v >> (32 - 1 - b)) & ((1 << (b - a + 1)) - 1);')
  w0('}')
  w0('')
  w0('#define PPC_DECODER_MISS assert_always(); return PPCOpcode::kInvalid')
  w0('#define PPC_DECODER_HIT(name) return PPCOpcode::name;')
  w0('')
  w0('PPCOpcode LookupOpcode(uint32_t code) {')
  w1('switch (ExtractBits(code, 0, 5)) {')

  subtables = {}
  for i in sorted(insns, key = lambda i: i.op_primary):
    if i.op_primary not in subtables: subtables[i.op_primary] = []
    subtables[i.op_primary].append(i)

  for pri in sorted(subtables.iterkeys()):
    # all the extended encodings (which we care about) end with bit 30. So we want to
    # do the rest of the seach by bitscanning left from bit 30. This is simulated
    # in the C switch-statement by creating leafs for each extended opcode,
    # sorted by bitlength shortest to longest.

    if len(subtables[pri]) == 1:
      for i in subtables[pri]:
        # the primary opcode field fully identifies the opcode
        w1('case %i: PPC_DECODER_HIT(%s);' % (i.op_primary, i.mnem))
      continue

    extract_groups = {}
    for i in subtables[pri]:
      form_parts = extended_opcode_bits[i.form]
      shift = 0
      for form_part in form_parts:
        shift = max(shift, form_part[1])
      extract_parts = []
      for form_part in form_parts:
        extract_parts.append('(ExtractBits(code, %s, %s) << %s)' % (form_part[0], form_part[1], shift - form_part[1]))
      extract_expression = '|'.join(extract_parts)
      if extract_expression not in extract_groups:
        extract_groups[extract_expression] = (i.form, extract_expression, [])
      extract_groups[extract_expression][2].append(i)

    w1('case %i:' % (pri))
    for extract_expression in sorted(extract_groups.iterkeys()):
      (form, extract_expression, group_insns) = extract_groups[extract_expression]
      bit_span_low = 31
      bit_span_high = 0
      form_parts = extended_opcode_bits[form]
      for form_part in form_parts:
        bit_span_low = min(bit_span_low, form_part[0])
        bit_span_high = max(bit_span_high, form_part[1])
      bit_count = bit_span_high - bit_span_low + 1
      w2('switch (%s) {' % (extract_expression))
      for i in sorted(group_insns, key=lambda i: i.op_extended):
        w3('case 0b%s: PPC_DECODER_HIT(%s);' % (
            ('{:0'+str(bit_count)+'b}').format(i.op_extended),
            i.mnem))
      w2('}')
    w2('PPC_DECODER_MISS;')

  w1('default: PPC_DECODER_MISS;')

  w1('}')
  w0('}')
  w0('')
  w0('}  // namespace ppc')
  w0('}  // namespace cpu')
  w0('}  // namespace xe')
  w0('')

  # from this we can see some tables have bits which can be used to determine extended opcoded size:
  # primary opcode 31:
  # 01... = 9 bits (XO form), else 10 bits (X/XFX forms)
  # primary opcode 63:
  # 1.... = 7 bits (A form), else 10 bits (X/XFL forms)
  # primary opcode 4:
  # does not have small bit range to determine size, but you can just use the
  # low 7 bits in order to "guess" the opcode. if you assume no invalid
  # encodings are input, only the sequence ...0001000 actually *needs* the upper
  # bits in order to differentiate the opcode (0100001000 = ps_abs, 0010001000 = ps_nabs)
  # otherwise, the low 7bits can be used as the determinant, and a second comparison
  # can be used against the real length of bits to fully match the extended opcode
  #
  # this approach can be generalized for all primary opcodes with extended opcodes of varying lengths:
  # compare bits of smallest length, fall through to comparing larger sizes until found or failure
  # with the optional optimization of discarding further compares for extended opcodes which
  # share top bits with any other extended opcode (at the price of failing to detect invalid opcodes)

  return '\n'.join(l)


if __name__ == '__main__':
  ppc_src_path = os.path.join(self_path, '..', 'src', 'xenia', 'cpu', 'ppc')
  insns = parse_insns(os.path.join(self_path, 'ppc-instructions.xml'))
  with open(os.path.join(ppc_src_path, 'ppc_opcode.h'), 'w') as f:
    f.write(generate_opcodes(insns))
  insns = parse_insns(os.path.join(self_path, 'ppc-instructions.xml'))
  with open(os.path.join(ppc_src_path, 'ppc_opcode_table.cc'), 'w') as f:
    f.write(generate_table(insns))
  insns = parse_insns(os.path.join(self_path, 'ppc-instructions.xml'))
  with open(os.path.join(ppc_src_path, 'ppc_opcode_lookup.cc'), 'w') as f:
    f.write(generate_lookup(insns))
