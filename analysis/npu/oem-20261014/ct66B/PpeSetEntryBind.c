
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void PpeSetEntryBind(long param_1,uint *param_2)

{
  uint uVar1;
  ushort uVar2;
  long lVar3;
  long lVar4;
  uint uVar5;
  int iVar6;
  uint *puVar7;
  uint local_58;
  undefined4 local_54;
  undefined4 uStack_50;
  undefined8 local_4c;
  long lStack_44;
  undefined4 uStack_3c;
  long local_38;
  
  lVar3 = sp_el0;
  puVar7 = param_2 + 4;
  local_38 = *(long *)(lVar3 + 0x3f0);
  uVar1 = *param_2;
  uVar5 = uVar1 & 0xe000000;
  if ((uVar1 & 0xc000000) != 0 && uVar5 != 0x6000000) {
    if (uVar5 == 0xe000000 || (uVar1 & 0xc000000) == 0x8000000) {
      puVar7 = param_2 + 0xb;
    }
    else {
      if (uVar5 != 0x4000000) goto LAB_00159c2c;
      puVar7 = param_2 + 0xb;
    }
  }
  local_54 = uVar1;
  FUN_0014cf54(&local_58);
  local_54 = local_54 & 0xffff8000 | local_58 & 0x7fff;
  if (((DAT_0019fb98 == 1) && (iVar6 = PpeCheckSoe(param_1), iVar6 == 0)) &&
     (iVar6 = FUN_0014c514(param_1,param_2), iVar6 < 0)) {
    if (2 < DebugLevel) {
      _printk("packet_check < 0!\n");
    }
    goto LAB_00159c2c;
  }
  uVar5 = 0;
  if (*(char *)(param_1 + 0x111) != '\x01') {
    uVar5 = (uint)((*puVar7 & 0x1e0) != 0x1e0);
  }
  local_54 = local_54 & 0xfe000000 | local_54 & 0xffffff | uVar5 << 0x18;
  local_4c = 0;
  uStack_50 = 4;
  lStack_44 = -0x100000000;
  uStack_3c = 0;
  iVar6 = __ECNT_HOOK(0x47,0,&uStack_50);
  if ((iVar6 != -1) && (-1 < lStack_44)) {
    local_54 = local_54 & 0xfeffffff;
  }
  uVar2 = (ushort)(((uint)((ulong)_DAT_0019fc88 >> 0x20) & 1) << 7) | 0x2000 |
          local_54._2_2_ & 0xcf7f;
  if ((DAT_0019fd28 & 1) == 0) {
    uVar5 = (uVar2 & 0xfff0) << 0x10 | local_54 & 0xffff | (DAT_0019fc1e & 0xf) << 0x10;
    if (DAT_0019fc20 != 0) goto LAB_00159c6c;
LAB_00159be4:
    iVar6 = 0;
  }
  else {
    uVar5 = (uVar2 & 0xfff0) << 0x10 | local_54 & 0xffff | (DAT_0019fcb8 & 0xf) << 0x10;
    if (DAT_0019fcbc == 0) goto LAB_00159be4;
LAB_00159c6c:
    iVar6 = 1;
  }
  local_54 = uVar5 & 0xff800000 | uVar5 & 0x3fffff | iVar6 << 0x16;
  iVar6 = GET_HIR();
  if (((iVar6 != 10) && (iVar6 = GET_HIR(), iVar6 != 0xc)) &&
     ((iVar6 = GET_HIR(), iVar6 != 0xe && (iVar6 = GET_HIR(), iVar6 != 0xf)))) {
    GET_HIR();
  }
  iVar6 = ppe_is_multicast_entry(param_2);
  if ((((iVar6 != 0) && (iVar6 = GET_HIR(), iVar6 != 10)) && (iVar6 = GET_HIR(), iVar6 != 0xc)) &&
     ((iVar6 = GET_HIR(), iVar6 != 0xe && (iVar6 = GET_HIR(), iVar6 != 0xf)))) {
    GET_HIR();
  }
  ecnt_ppe_set_entry_bind_hook(param_1,param_2,&local_54);
  *param_2 = local_54;
LAB_00159c2c:
  lVar4 = sp_el0;
  lVar3 = local_38 - *(long *)(lVar4 + 0x3f0);
  if (lVar3 == 0) {
    return;
  }
                    /* WARNING: Subroutine does not return */
  __stack_chk_fail(lVar4,0,lVar3);
}

