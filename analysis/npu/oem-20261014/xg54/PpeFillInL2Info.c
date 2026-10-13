
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 PpeFillInL2Info(long param_1,uint *param_2)

{
  ushort uVar1;
  ushort uVar2;
  ushort uVar3;
  ushort uVar4;
  undefined2 uVar5;
  uint uVar6;
  int iVar7;
  ushort uVar8;
  undefined4 local_30;
  undefined2 local_2c;
  
  if ((*param_2 & 0x30000000) == 0x20000000) {
    if ((*(ushort *)(param_1 + 0xce) == hwnat_dbg_bindfail_idx) &&
       (iVar7 = __printk_ratelimit("PpeFillInL2Info"), iVar7 != 0)) {
      printk("%s,%d:entry is already bind\n","PpeFillInL2Info",0x9b9);
      return 1;
    }
    return 1;
  }
  uVar5 = 0x3f;
  if ((_TCSUPPORT_DP_MVAL >> 0xb & 1) == 0) {
    PpeClearEntryInfo(param_2);
  }
  else {
    uVar5 = PpeGetAcntGrpIdFromEntry(param_2);
    PpeClearEntryInfo(param_2);
  }
  uVar1 = DAT_00193d9c;
  if ((_TCSUPPORT_DP_MVAL >> 0xb & 1) != 0) {
    PpeSetAcntGrpId(param_2,uVar5);
    uVar1 = DAT_00193d9c;
  }
  DAT_00193d9c = uVar1;
  if ((uint)DAT_00193e08 < 2) {
    if ((*param_2 & 0xe000000) == 0x6000000) {
      FoeSetMacInfo(param_2 + 0xe,0x193d8e);
      FoeSetMacInfo(param_2 + 0xc,&PpeParseResult);
    }
    else {
      FoeSetMacInfo(param_2 + 0xc,&PpeParseResult);
      FoeSetMacInfo(param_2 + 0xe,0x193d8e);
    }
    uVar4 = DAT_00193da6;
    uVar2 = DAT_00193d94 >> 8;
    uVar1 = DAT_00193d94 << 8;
    uVar3 = DAT_00193d9c >> 8;
    uVar8 = DAT_00193d9c << 8;
    *(ushort *)(param_2 + 0xb) = DAT_00193d98 >> 8 | DAT_00193d98 << 8;
    *(ushort *)((long)param_2 + 0x2e) = uVar2 | uVar1;
    *(ushort *)(param_2 + 0xd) = uVar3 | uVar8;
    *(ushort *)(param_2 + 0xf) = uVar4 >> 8 | uVar4 << 8;
    return 0;
  }
  if ((uint)DAT_00193e08 == 2) {
    uVar2 = DAT_00193d94 >> 8;
    uVar8 = DAT_00193d94 << 8;
    *(ushort *)(param_2 + 0xc) = DAT_00193d98 >> 8 | DAT_00193d98 << 8;
    *(ushort *)((long)param_2 + 0x32) = uVar2 | uVar8;
    *(ushort *)(param_2 + 0xe) = uVar1 >> 8 | uVar1 << 8;
    if ((_DAT_00196384 >> 4 & 1) == 0) {
      return 0;
    }
    if ((param_2[1] == PpeParseResult) && ((short)param_2[2] == (short)DAT_00193d8c)) {
      return 0;
    }
    if (*(ushort *)(param_1 + 0xce) != hwnat_dbg_bindfail_idx) {
      return 1;
    }
    iVar7 = __printk_ratelimit("PpeFillInL2Info");
    if (iVar7 != 0) {
      printk("%s,%d:check dmac fail\n","PpeFillInL2Info",0x9dd);
      return 1;
    }
    return 1;
  }
  iVar7 = GET_HIR();
  if ((((iVar7 != 10) && (iVar7 = GET_HIR(), iVar7 != 0xc)) && (iVar7 = GET_HIR(), iVar7 != 0xe)) ||
     ((uint)DAT_00193e08 == 3)) {
    FoeSetMacInfo(param_2 + 0xc,&PpeParseResult);
    FoeSetMacInfo(param_2 + 0xe,0x193d8e);
    iVar7 = GET_HIR();
    goto joined_r0x0013ec58;
  }
  iVar7 = cmpMacInfo(0x193d8e,param_1 + 0xd4);
  if (iVar7 == 0) {
LAB_0013eb68:
    param_2[0xf] = param_2[0xf] & 0xffe00000 | param_2[0xf] & 0xffff | 0xf0000;
  }
  else {
    local_30 = ram0x00193d8e;
    local_2c = DAT_00193d90._2_2_;
    uVar6 = find_and_update_shrink_table(0,&local_30);
    if (uVar6 == 0xffffffff) {
      printk("smac: find and update shrink table failed!\n");
    }
    else {
      if ((uVar6 & 0xff) == 0x10) goto LAB_0013eb68;
      param_2[0xf] = param_2[0xf] & 0xffe00000 | param_2[0xf] & 0xffff | (uVar6 & 0x1f) << 0x10;
    }
  }
  FoeSetMacInfo(param_2 + 0xd,&PpeParseResult);
  iVar7 = GET_HIR();
joined_r0x0013ec58:
  if (((iVar7 == 10) || (iVar7 = GET_HIR(), iVar7 == 0xc)) || (iVar7 = GET_HIR(), iVar7 == 0xe)) {
    uVar1 = DAT_00193d94 >> 8 | DAT_00193d94 << 8;
    uVar8 = DAT_00193d98 >> 8 | DAT_00193d98 << 8;
    uVar2 = DAT_00193d9c >> 8 | DAT_00193d9c << 8;
    uVar3 = DAT_00193da6 >> 8 | DAT_00193da6 << 8;
    if ((uint)DAT_00193e08 == 3) {
      *(ushort *)(param_2 + 0xb) = uVar8;
      *(ushort *)((long)param_2 + 0x2e) = uVar1;
      *(ushort *)(param_2 + 0xd) = uVar2;
      *(ushort *)(param_2 + 0xf) = uVar3;
      return 0;
    }
  }
  else {
    uVar1 = DAT_00193d94 >> 8 | DAT_00193d94 << 8;
    uVar8 = DAT_00193d98 >> 8 | DAT_00193d98 << 8;
    uVar2 = DAT_00193d9c >> 8 | DAT_00193d9c << 8;
    uVar3 = DAT_00193da6 >> 8 | DAT_00193da6 << 8;
  }
  *(ushort *)(param_2 + 0xc) = uVar8;
  *(ushort *)((long)param_2 + 0x32) = uVar1;
  *(ushort *)(param_2 + 0xe) = uVar2;
  *(ushort *)(param_2 + 0xf) = uVar3;
  return 0;
}

