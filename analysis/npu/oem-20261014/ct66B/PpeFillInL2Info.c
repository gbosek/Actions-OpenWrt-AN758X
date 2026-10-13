
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void PpeFillInL2Info(long param_1,uint *param_2)

{
  ushort uVar1;
  ushort uVar2;
  long lVar3;
  ushort uVar4;
  ushort uVar5;
  ushort uVar6;
  ushort uVar7;
  undefined2 uVar8;
  uint uVar9;
  int iVar10;
  undefined8 uVar11;
  undefined4 *puVar12;
  uint *puVar13;
  long lVar14;
  undefined4 local_70;
  undefined2 local_6c;
  int local_3e;
  short local_3a;
  long local_38;
  
  lVar14 = sp_el0;
  local_38 = *(long *)(lVar14 + 0x3f0);
  local_3e = 0;
  local_3a = 0;
  if ((*param_2 & 0x30000000) == 0x20000000) {
    if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
       (iVar10 = __printk_ratelimit("PpeFillInL2Info"), iVar10 != 0)) {
      _printk("%s,%d:entry is already bind\n","PpeFillInL2Info",0xb1c);
      uVar11 = 1;
      goto LAB_0015281c;
    }
LAB_001529b8:
    uVar11 = 1;
    goto LAB_0015281c;
  }
  uVar8 = 0x3f;
  if ((_TCSUPPORT_DP_MVAL >> 0xb & 1) == 0) {
    PpeClearEntryInfo(param_2);
    if ((_TCSUPPORT_DP_MVAL >> 0xb & 1) != 0) goto LAB_00152868;
LAB_001527c8:
    if (DAT_0019fc88 < 2) goto LAB_0015288c;
LAB_001527e0:
    uVar2 = DAT_0019fc1c;
    if (DAT_0019fc88 == 2) {
      uVar4 = DAT_0019fc14 >> 8;
      uVar1 = DAT_0019fc14 << 8;
      *(ushort *)(param_2 + 0xc) = DAT_0019fc18 >> 8 | DAT_0019fc18 << 8;
      *(ushort *)((long)param_2 + 0x32) = uVar4 | uVar1;
      *(ushort *)(param_2 + 0xe) = uVar2 >> 8 | uVar2 << 8;
      if (((_DAT_001a21ac >> 4 & 1) != 0) &&
         ((FoeSetEntryMac(&local_3e,param_2 + 1,(long)param_2 + 10), local_3e != PpeParseResult ||
          (local_3a != DAT_0019fc0c)))) {
        if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
           (iVar10 = __printk_ratelimit("PpeFillInL2Info"), iVar10 != 0)) {
          _printk("%s,%d:check dmac fail\n","PpeFillInL2Info",0xb41);
          uVar11 = 1;
          goto LAB_0015281c;
        }
        goto LAB_001529b8;
      }
    }
    else {
      iVar10 = GET_HIR();
      if (((((iVar10 == 10) || (iVar10 = GET_HIR(), iVar10 == 0xc)) ||
           (iVar10 = GET_HIR(), iVar10 == 0xe)) ||
          ((iVar10 = GET_HIR(), iVar10 == 0xf || (iVar10 = GET_HIR(), iVar10 == 0x10)))) &&
         (DAT_0019fc88 != 3)) {
        iVar10 = cmpMacInfo(&DAT_0019fc0e,param_1 + 0x135);
        if (iVar10 == 0) {
LAB_00152af4:
          param_2[0xf] = param_2[0xf] & 0xffe00000 | param_2[0xf] & 0xffff | 0xf0000;
        }
        else {
          local_70 = DAT_0019fc0e;
          local_6c = DAT_0019fc12;
          uVar9 = find_and_update_shrink_table(0,&local_70);
          if (uVar9 == 0xffffffff) {
            _printk("smac: find and update shrink table failed!\n");
          }
          else {
            if ((uVar9 & 0xff) == 0x10) goto LAB_00152af4;
            param_2[0xf] = param_2[0xf] & 0xffe00000 |
                           param_2[0xf] & 0xffff | (uVar9 & 0x1f) << 0x10;
          }
        }
        FoeSetEntryMac(&PpeParseResult,param_2 + 0xd,(long)param_2 + 0x3a);
      }
      else {
        FoeSetEntryMac(&PpeParseResult,param_2 + 0xc,(long)param_2 + 0x36);
        FoeSetEntryMac(&DAT_0019fc0e,param_2 + 0xe,(long)param_2 + 0x3e);
      }
      iVar10 = GET_HIR();
      if ((((iVar10 == 10) || (iVar10 = GET_HIR(), iVar10 == 0xc)) ||
          ((iVar10 = GET_HIR(), iVar10 == 0xe ||
           ((iVar10 = GET_HIR(), iVar10 == 0xf || (iVar10 = GET_HIR(), iVar10 == 0x10)))))) &&
         (DAT_0019fc88 == 3)) {
        uVar5 = DAT_0019fc26 >> 8;
        uVar2 = DAT_0019fc26 << 8;
        uVar6 = DAT_0019fc1c >> 8;
        uVar1 = DAT_0019fc1c << 8;
        uVar7 = DAT_0019fc14 >> 8;
        uVar4 = DAT_0019fc14 << 8;
        *(ushort *)(param_2 + 0xb) = DAT_0019fc18 >> 8 | DAT_0019fc18 << 8;
        *(ushort *)((long)param_2 + 0x2e) = uVar7 | uVar4;
        *(ushort *)(param_2 + 0xd) = uVar6 | uVar1;
        *(ushort *)(param_2 + 0xf) = uVar5 | uVar2;
      }
      else {
        uVar6 = DAT_0019fc26;
        uVar4 = DAT_0019fc14 >> 8;
        uVar2 = DAT_0019fc14 << 8;
        uVar5 = DAT_0019fc1c >> 8;
        uVar1 = DAT_0019fc1c << 8;
        *(ushort *)(param_2 + 0xc) = DAT_0019fc18 >> 8 | DAT_0019fc18 << 8;
        *(ushort *)((long)param_2 + 0x32) = uVar4 | uVar2;
        *(ushort *)(param_2 + 0xe) = uVar5 | uVar1;
        *(ushort *)(param_2 + 0xf) = uVar6 >> 8 | uVar6 << 8;
      }
    }
  }
  else {
    uVar8 = PpeGetAcntGrpIdFromEntry(param_2,0);
    PpeClearEntryInfo(param_2);
    if ((_TCSUPPORT_DP_MVAL >> 0xb & 1) == 0) goto LAB_001527c8;
LAB_00152868:
    PpeSetAcntGrpId(param_2,uVar8);
    if (1 < DAT_0019fc88) goto LAB_001527e0;
LAB_0015288c:
    puVar12 = &PpeParseResult;
    if ((*param_2 & 0xe000000) == 0x6000000) {
      FoeSetEntryMac(&DAT_0019fc0e,param_2 + 0xe,(long)param_2 + 0x3e);
      lVar14 = (long)param_2 + 0x36;
      puVar13 = param_2 + 0xc;
    }
    else {
      FoeSetEntryMac(&PpeParseResult,param_2 + 0xc,(long)param_2 + 0x36);
      puVar12 = &DAT_0019fc0e;
      lVar14 = (long)param_2 + 0x3e;
      puVar13 = param_2 + 0xe;
    }
    FoeSetEntryMac(puVar12,puVar13,lVar14);
    uVar6 = DAT_0019fc26;
    uVar4 = DAT_0019fc14 >> 8;
    uVar2 = DAT_0019fc14 << 8;
    uVar5 = DAT_0019fc1c >> 8;
    uVar1 = DAT_0019fc1c << 8;
    *(ushort *)(param_2 + 0xb) = DAT_0019fc18 >> 8 | DAT_0019fc18 << 8;
    *(ushort *)((long)param_2 + 0x2e) = uVar4 | uVar2;
    *(ushort *)(param_2 + 0xd) = uVar5 | uVar1;
    *(ushort *)(param_2 + 0xf) = uVar6 >> 8 | uVar6 << 8;
  }
  uVar11 = 0;
LAB_0015281c:
  lVar3 = sp_el0;
  lVar14 = local_38 - *(long *)(lVar3 + 0x3f0);
  if (lVar14 != 0) {
                    /* WARNING: Subroutine does not return */
    __stack_chk_fail(uVar11,lVar3,0,lVar14);
  }
  return;
}

